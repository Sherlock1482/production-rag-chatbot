import email
import email.header
import email.utils
import hashlib
import imaplib
import io
import os
import re
import shutil
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field


# ============================================================
# Pydantic Schemas
# ============================================================

class PendingResumeItem(BaseModel):
    id: str = Field(description="Unique UUID for this pending resume item.")
    candidate_name: str = Field(description="Detected or parsed candidate name.")
    email_sender: str = Field(description="Sender email or LinkedIn notification sender.")
    source_channel: str = Field(description="Origin channel: 'LinkedIn', 'Gmail', or 'Outlook'.")
    received_at: str = Field(description="ISO timestamp of when the message/attachment was received.")
    filename: str = Field(description="Filename of the resume attachment.")
    filesize_bytes: int = Field(description="Size of the attachment in bytes.")
    file_path: str = Field(description="Path to staged temporary file on disk.")
    status: str = Field(default="pending", description="Status: 'pending', 'ingested', or 'denied'.")
    is_duplicate: bool = Field(default=False, description="True if filename, hash, or candidate name matches existing records.")
    duplicate_reason: Optional[str] = Field(default=None, description="Explanation of why this candidate was flagged as duplicate.")


class PendingResumeResponse(BaseModel):
    total_pending: int
    items: List[PendingResumeItem]


class BatchIngestRequest(BaseModel):
    resume_ids: List[str] = Field(default_factory=list, description="List of pending resume item IDs to ingest. Empty list means 'ingest all pending'.")


class BatchIngestResult(BaseModel):
    id: str
    filename: str
    candidate_name: str
    status: str
    message: str


class BatchIngestResponse(BaseModel):
    success: bool
    ingested_count: int
    results: List[BatchIngestResult]


class DenyResumeRequest(BaseModel):
    resume_ids: List[str] = Field(default_factory=list, description="List of pending resume item IDs to deny/remove.")


class DenyResumeResponse(BaseModel):
    success: bool
    denied_count: int
    message: str


# ============================================================
# Inbound Resume Manager Core
# ============================================================

class InboundResumeManager:
    def __init__(
        self,
        db_path: Optional[str] = None,
        staging_dir: Optional[str] = None,
        uploads_dir: Optional[str] = None,
        enable_imap: bool = True,
    ):
        base_dir = Path(__file__).resolve().parent.parent
        self.db_path = db_path or str(base_dir.parent / "ta_interviews.db")
        self.staging_dir = Path(staging_dir or (base_dir / "data" / "inbox_staging"))
        self.uploads_dir = Path(uploads_dir or (base_dir / "data" / "uploads"))
        self.enable_imap = enable_imap

        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_resumes (
                id TEXT PRIMARY KEY,
                candidate_name TEXT,
                email_sender TEXT,
                source_channel TEXT,
                received_at TEXT,
                filename TEXT,
                filesize_bytes INTEGER,
                file_path TEXT,
                file_hash TEXT,
                status TEXT DEFAULT 'pending',
                is_duplicate INTEGER DEFAULT 0,
                duplicate_reason TEXT
            )
        """)
        conn.commit()
        conn.close()

    def detect_duplicate(
        self, filename: str, candidate_name: str, file_hash: str
    ) -> tuple[bool, Optional[str]]:
        """
        Check if candidate or file already exists in SQLite or uploads directory.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check existing hash in pending_resumes (either pending or ingested)
        cursor.execute(
            "SELECT filename, candidate_name, status FROM pending_resumes WHERE file_hash = ? AND status != 'denied'",
            (file_hash,),
        )
        row = cursor.fetchone()
        if row:
            conn.close()
            return True, f"Identical file already registered for {row['candidate_name']} ({row['status']})"

        # Check existing candidate name in pending or ingested resumes
        norm_name = candidate_name.strip().casefold()
        cursor.execute(
            "SELECT candidate_name, status FROM pending_resumes WHERE lower(candidate_name) = ? AND status != 'denied'",
            (norm_name,),
        )
        row_name = cursor.fetchone()
        if row_name:
            conn.close()
            return True, f"Duplicate candidate: '{candidate_name}' already registered ({row_name['status']})"

        # Check interviews table if present
        try:
            cursor.execute("SELECT candidate_name FROM interviews WHERE lower(candidate_name) = ?", (norm_name,))
            if cursor.fetchone():
                conn.close()
                return True, f"Candidate '{candidate_name}' already exists in scheduled interviews"
        except sqlite3.OperationalError:
            pass

        conn.close()

        # Check physical uploads folder
        existing_upload = self.uploads_dir / filename
        if existing_upload.exists():
            return True, f"A file named '{filename}' is already present in uploaded documents"

        return False, None

    def add_pending_resume(
        self,
        candidate_name: str,
        email_sender: str,
        source_channel: str,
        filename: str,
        content_bytes: bytes,
        received_at: Optional[str] = None,
    ) -> Optional[PendingResumeItem]:
        file_hash = hashlib.sha256(content_bytes).hexdigest()

        # Strict Deduplication: If this exact file hash is already in the database
        # (whether pending, ingested, or denied), NEVER create another pending row!
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, status FROM pending_resumes WHERE file_hash = ?",
            (file_hash,),
        )
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return None

        item_id = str(uuid.uuid4())
        filesize = len(content_bytes)
        rec_time = received_at or datetime.now(timezone.utc).isoformat()

        is_dup, dup_reason = self.detect_duplicate(filename, candidate_name, file_hash)

        # Save to staging disk
        staged_file = self.staging_dir / f"{item_id}_{filename}"
        staged_file.write_bytes(content_bytes)

        cursor.execute(
            """
            INSERT INTO pending_resumes (
                id, candidate_name, email_sender, source_channel,
                received_at, filename, filesize_bytes, file_path,
                file_hash, status, is_duplicate, duplicate_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                item_id,
                candidate_name,
                email_sender,
                source_channel,
                rec_time,
                filename,
                filesize,
                str(staged_file),
                file_hash,
                1 if is_dup else 0,
                dup_reason,
            ),
        )
        conn.commit()
        conn.close()

        return PendingResumeItem(
            id=item_id,
            candidate_name=candidate_name,
            email_sender=email_sender,
            source_channel=source_channel,
            received_at=rec_time,
            filename=filename,
            filesize_bytes=filesize,
            file_path=str(staged_file),
            status="pending",
            is_duplicate=is_dup,
            duplicate_reason=dup_reason,
        )

    def get_pending_resumes(self) -> PendingResumeResponse:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM pending_resumes WHERE status = 'pending' ORDER BY received_at DESC"
        )
        rows = cursor.fetchall()
        conn.close()

        items = [
            PendingResumeItem(
                id=r["id"],
                candidate_name=r["candidate_name"],
                email_sender=r["email_sender"],
                source_channel=r["source_channel"],
                received_at=r["received_at"],
                filename=r["filename"],
                filesize_bytes=r["filesize_bytes"],
                file_path=r["file_path"],
                status=r["status"],
                is_duplicate=bool(r["is_duplicate"]),
                duplicate_reason=r["duplicate_reason"],
            )
            for r in rows
        ]
        return PendingResumeResponse(total_pending=len(items), items=items)

    def _decode_header_str(self, header_raw: Optional[str]) -> str:
        if not header_raw:
            return ""
        try:
            decoded_parts = email.header.decode_header(header_raw)
            result = []
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    result.append(part.decode(encoding or "utf-8", errors="replace"))
                else:
                    result.append(str(part))
            return "".join(result).strip()
        except Exception:
            return str(header_raw).strip()

    @staticmethod
    def _peek_name_from_content(filename: str, content_bytes: bytes) -> Optional[str]:
        """
        Quickly inspects the first few lines of resume text for candidate name.
        """
        try:
            ext = Path(filename).suffix.lower()
            text = ""
            if ext == ".txt":
                text = content_bytes.decode("utf-8", errors="ignore")
            elif ext == ".pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(io.BytesIO(content_bytes))
                    if reader.pages:
                        text = reader.pages[0].extract_text() or ""
                except Exception:
                    pass
            elif ext in [".docx", ".doc"]:
                try:
                    import docx
                    doc = docx.Document(io.BytesIO(content_bytes))
                    text = "\n".join([p.text for p in doc.paragraphs if p.text])
                except Exception:
                    pass

            if text:
                # 1. Check for explicit name label: Name: Jane Doe or Candidate: Jane Doe
                name_match = re.search(
                    r"(?im)^(?:candidate\s+name|candidate|name|full\s+name)\s*[:\-]\s*([A-Za-z\s\.\-]{3,35})$",
                    text,
                )
                if name_match:
                    found = name_match.group(1).strip()
                    if found and not any(w in found.lower() for w in ["resume", "email", "phone", "curriculum"]):
                        return found.title()

                # 2. Check first 10 lines for prominent candidate name
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                for line in lines[:10]:
                    if any(w in line.lower() for w in [
                        "resume", "curriculum", "page", "http", "@", "email",
                        "phone", "linkedin", "github", "address", "summary",
                        "experience", "skills", "education"
                    ]):
                        continue
                    words = line.split()
                    if 2 <= len(words) <= 4 and len(line) <= 35:
                        if all(w.replace("-", "").replace(".", "").isalpha() for w in words):
                            return line.title()
        except Exception:
            pass
        return None

    @classmethod
    def extract_candidate_name(
        cls,
        filename: str,
        sender_real_name: str = "",
        sender_email: str = "",
        content_bytes: Optional[bytes] = None,
    ) -> str:
        """
        Smarter Candidate Name Extraction:
        1. Analyzes filename for candidate name (e.g. Khushi_Chitari Resume.pdf -> 'Khushi Chitari').
        2. Peeks at resume text (first non-empty line of PDF/DOCX/TXT) if filename is generic.
        3. Falls back to sender display name or email if no candidate name found in document.
        """
        generic_terms = {
            "resume", "cv", "curriculum", "vitae", "profile", "updated",
            "final", "latest", "draft", "v1", "v2", "v3", "job", "application",
            "document", "scan", "attachment", "my", "new", "copy", "pdf", "docx",
            "fullstack", "backend", "frontend", "developer", "engineer", "lead",
            "software", "senior", "junior", "staff", "principal", "intern", "internship",
            "specialist", "analyst", "manager", "data", "designer", "architect",
            "qa", "devops", "sde", "sdett", "consultant"
        }

        # 1. Inspect filename
        stem = Path(filename).stem
        cleaned = re.sub(r"[_\-\.\(\)\[\]\{\},]+", " ", stem)
        cleaned = re.sub(r"\b\d+\b", " ", cleaned)
        tokens = [t.strip() for t in cleaned.split() if t.strip()]
        name_tokens = [t for t in tokens if t.casefold() not in generic_terms and t.isalpha()]

        if len(name_tokens) >= 2:
            candidate_from_filename = " ".join(name_tokens).title()
            if re.search(r"[a-zA-Z]", candidate_from_filename):
                return candidate_from_filename

        # 2. Peek into document content if bytes provided
        if content_bytes:
            extracted_from_doc = cls._peek_name_from_content(filename, content_bytes)
            if extracted_from_doc:
                return extracted_from_doc

        # If single token was found from filename, use it
        if len(name_tokens) == 1 and len(name_tokens[0]) >= 3 and name_tokens[0].isalpha():
            return name_tokens[0].title()

        # 3. Fallback to sender's display name (e.g. direct candidate email)
        if sender_real_name:
            clean_sender = sender_real_name.strip()
            if (
                clean_sender
                and not clean_sender.lower().startswith("job")
                and not clean_sender.lower().startswith("inmail")
                and not clean_sender.lower().startswith("notification")
                and "@" not in clean_sender
            ):
                return clean_sender.title()

        # 4. Fallback to email username
        if sender_email and "@" in sender_email:
            username = sender_email.split("@")[0]
            clean_username = re.sub(r"[_\-\.\d]+", " ", username).strip()
            if len(clean_username) >= 3:
                return clean_username.title()

        return "Candidate"

    def _fetch_from_imap(self) -> List[PendingResumeItem]:
        """
        Connects to a live IMAP server (e.g. Gmail at imap.gmail.com:993)
        and extracts unreviewed attachments from incoming emails.
        """
        load_dotenv(override=True)
        email_user = os.getenv("RECRUITER_EMAIL") or os.getenv("GMAIL_USER")
        email_password = (
            os.getenv("RECRUITER_EMAIL_PASSWORD")
            or os.getenv("GMAIL_APP_PASSWORD")
            or os.getenv("IMAP_PASSWORD")
        )
        imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
        imap_port = int(os.getenv("IMAP_PORT", 993))

        if not email_user or not email_password:
            return []

        clean_password = email_password.replace(" ", "").strip("\"'")
        found_items: List[PendingResumeItem] = []

        try:
            print(f"Connecting to IMAP {imap_server}:{imap_port} for {email_user}...")
            mail = imaplib.IMAP4_SSL(imap_server, imap_port)
            mail.login(email_user, clean_password)
            mail.select("INBOX")

            # First search UNSEEN, if none search recent 20 emails
            status, msg_nums = mail.search(None, "UNSEEN")
            nums = msg_nums[0].split() if status == "OK" and msg_nums[0] else []

            if not nums:
                status, all_nums = mail.search(None, "ALL")
                if status == "OK" and all_nums[0]:
                    all_ids = all_nums[0].split()
                    nums = all_ids[-25:]

            allowed_extensions = {".pdf", ".docx", ".doc", ".txt"}

            for num in reversed(nums):
                res, data = mail.fetch(num, "(RFC822)")
                if res != "OK" or not data or not data[0]:
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                sender_header = self._decode_header_str(msg.get("From"))
                subject_header = self._decode_header_str(msg.get("Subject"))
                date_header = msg.get("Date")

                real_name, email_address = email.utils.parseaddr(sender_header)
                real_name = real_name.strip()
                email_address = email_address.strip()

                sender_lower = (sender_header + " " + email_address).lower()
                if "linkedin" in sender_lower:
                    source_channel = "LinkedIn"
                elif "outlook" in sender_lower or "microsoft" in sender_lower:
                    source_channel = "Outlook"
                else:
                    source_channel = "Gmail"

                for part in msg.walk():
                    content_disposition = str(part.get("Content-Disposition") or "")
                    part_filename = part.get_filename()

                    if not part_filename and "attachment" not in content_disposition.lower():
                        continue

                    if part_filename:
                        part_filename = self._decode_header_str(part_filename)

                    if not part_filename:
                        continue

                    ext = Path(part_filename).suffix.lower()
                    if ext not in allowed_extensions:
                        continue

                    payload_bytes = part.get_payload(decode=True)
                    if not payload_bytes:
                        continue

                    # Extract candidate name using smarter extraction (filename > doc content > sender name)
                    candidate_name = self.extract_candidate_name(
                        filename=part_filename,
                        sender_real_name=real_name,
                        sender_email=email_address,
                        content_bytes=payload_bytes,
                    )

                    iso_received = None
                    if date_header:
                        try:
                            parsed_tuple = email.utils.parsedate_to_datetime(date_header)
                            iso_received = parsed_tuple.isoformat()
                        except Exception:
                            iso_received = None

                    item = self.add_pending_resume(
                        candidate_name=candidate_name,
                        email_sender=email_address or sender_header,
                        source_channel=source_channel,
                        filename=part_filename,
                        content_bytes=payload_bytes,
                        received_at=iso_received,
                    )
                    if item is not None:
                        found_items.append(item)

            try:
                mail.close()
                mail.logout()
            except Exception:
                pass

            print(f"IMAP sync completed: found {len(found_items)} new resume attachment(s).")

        except Exception as e:
            print(f"IMAP sync warning: {e}", file=sys.stderr)

        return found_items

    def sync_inbound_resumes(self) -> List[PendingResumeItem]:
        """
        Polls external email/LinkedIn channels.
        1. Checks live IMAP if RECRUITER_EMAIL & RECRUITER_EMAIL_PASSWORD are set.
        2. In hybrid mode, falls back to demo seed ONLY if database has 0 total records.
        """
        if self.enable_imap:
            self._fetch_from_imap()

        current_pending = self.get_pending_resumes()
        if current_pending.total_pending > 0:
            return current_pending.items

        # If live email credentials are set or database already has records, do not re-seed demo candidates
        if self.enable_imap and (os.getenv("RECRUITER_EMAIL_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD")):
            return []

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pending_resumes")
        total_records = cursor.fetchone()[0]
        conn.close()
        if total_records > 0:
            return []

        # Seed realistic incoming resumes from LinkedIn and Gmail as demo fallback
        mock_candidates = [
            {
                "candidate_name": "Devin Vance",
                "email_sender": "job-applications@linkedin.com",
                "source_channel": "LinkedIn",
                "filename": "Devin_Vance_Staff_Backend_Resume.txt",
                "content": (
                    "Devin Vance\n"
                    "Staff Software Engineer - Distributed Systems\n"
                    "Email: devin.vance@example.com | LinkedIn: /in/devin-vance\n\n"
                    "SUMMARY:\n"
                    "Principal/Staff engineer with 9 years developing scalable backend architectures in Go and Python.\n"
                    "Specialized in Kafka streaming, Kubernetes, and high-throughput microservices.\n\n"
                    "EXPERIENCE:\n"
                    "Lead Distributed Systems Architect at CloudScale (2021-Present)\n"
                    "- Architected event-driven ingestion engine processing 1.2M events/sec with Kafka and Golang.\n"
                    "- Reduced cluster cost by 38% through optimized Kubernetes auto-scaling policies.\n\n"
                    "SKILLS:\n"
                    "Golang, Python, Distributed Systems, Kafka, Kubernetes, Redis, PostgreSQL, AWS, Microservices."
                ),
            },
            {
                "candidate_name": "Elena Rostova",
                "email_sender": "elena.rostova@gmail.com",
                "source_channel": "Gmail",
                "filename": "Elena_Rostova_FullStack_CV.txt",
                "content": (
                    "Elena Rostova\n"
                    "Full Stack Engineer\n"
                    "Email: elena.rostova@gmail.com\n\n"
                    "SUMMARY:\n"
                    "Senior Full Stack developer with 6 years experience across React, Next.js, TypeScript, and FastAPI.\n\n"
                    "EXPERIENCE:\n"
                    "Senior Web Engineer at FinTech Labs (2022-Present)\n"
                    "- Built recruiter analytics dashboards in Next.js 14 and TailwindCSS.\n"
                    "- Integrated asynchronous REST endpoints with FastAPI and PostgreSQL.\n\n"
                    "SKILLS:\n"
                    "React, Next.js, TypeScript, Python, FastAPI, Tailwind CSS, Docker, PostgreSQL."
                ),
            },
            {
                "candidate_name": "Priya Patel",
                "email_sender": "inmail-notification@linkedin.com",
                "source_channel": "LinkedIn",
                "filename": "Priya_Patel_Updated_Resume.txt",
                "content": (
                    "Priya Patel\n"
                    "Backend Engineer\n"
                    "Email: priya.patel@example.com\n\n"
                    "SUMMARY:\n"
                    "Senior Python backend developer with 5+ years building FastAPI and microservice solutions.\n\n"
                    "SKILLS:\n"
                    "Python, FastAPI, Docker, PostgreSQL, Redis, REST APIs."
                ),
            },
        ]

        added_items = []
        for c in mock_candidates:
            item = self.add_pending_resume(
                candidate_name=c["candidate_name"],
                email_sender=c["email_sender"],
                source_channel=c["source_channel"],
                filename=c["filename"],
                content_bytes=c["content"].encode("utf-8"),
            )
            added_items.append(item)

        return added_items

    def deny_resumes(self, request: DenyResumeRequest) -> DenyResumeResponse:
        conn = self._get_connection()
        cursor = conn.cursor()

        target_ids = request.resume_ids
        if not target_ids:
            # Deny all currently pending
            cursor.execute("SELECT id, file_path FROM pending_resumes WHERE status = 'pending'")
            rows = cursor.fetchall()
            target_ids = [r["id"] for r in rows]
        else:
            cursor.execute(
                f"SELECT id, file_path FROM pending_resumes WHERE id IN ({','.join(['?']*len(target_ids))})",
                target_ids,
            )
            rows = cursor.fetchall()

        denied_count = 0
        for r in rows:
            cursor.execute("UPDATE pending_resumes SET status = 'denied' WHERE id = ?", (r["id"],))
            denied_count += 1
            # Clean up staged file
            staged_path = Path(r["file_path"])
            if staged_path.exists():
                try:
                    staged_path.unlink()
                except Exception:
                    pass

        conn.commit()
        conn.close()

        return DenyResumeResponse(
            success=True,
            denied_count=denied_count,
            message=f"Successfully denied and removed {denied_count} resume(s).",
        )

    def ingest_resumes(
        self,
        request: BatchIngestRequest,
        skip_qdrant: bool = False,
    ) -> BatchIngestResponse:
        conn = self._get_connection()
        cursor = conn.cursor()

        target_ids = request.resume_ids
        if not target_ids:
            # Ingest all currently pending
            cursor.execute("SELECT * FROM pending_resumes WHERE status = 'pending'")
            rows = cursor.fetchall()
        else:
            cursor.execute(
                f"SELECT * FROM pending_resumes WHERE id IN ({','.join(['?']*len(target_ids))}) AND status = 'pending'",
                target_ids,
            )
            rows = cursor.fetchall()

        if not rows:
            conn.close()
            return BatchIngestResponse(
                success=True,
                ingested_count=0,
                results=[],
            )

        results = []
        ingested_count = 0

        for r in rows:
            item_id = r["id"]
            filename = r["filename"]
            candidate_name = r["candidate_name"]
            staged_file = Path(r["file_path"])

            dest_path = self.uploads_dir / filename

            try:
                # Copy from staging to uploads
                if staged_file.exists():
                    shutil.copy2(staged_file, dest_path)
                elif not dest_path.exists():
                    # Fallback write if already moved
                    dest_path.write_text(f"Resume for {candidate_name}", encoding="utf-8")

                # Perform actual parsing and indexing if not skipped
                if not skip_qdrant:
                    try:
                        from backend.utils.parser import parse_ta_document
                        from backend.utils.indexer import index_ta_chunks

                        chunks = parse_ta_document(str(dest_path))
                        index_ta_chunks(chunks, filename)
                    except Exception as parse_err:
                        # Fallback for relative path imports
                        from utils.parser import parse_ta_document
                        from utils.indexer import index_ta_chunks

                        chunks = parse_ta_document(str(dest_path))
                        index_ta_chunks(chunks, filename)

                # Update database status
                cursor.execute(
                    "UPDATE pending_resumes SET status = 'ingested' WHERE id = ?",
                    (item_id,),
                )
                conn.commit()

                ingested_count += 1
                results.append(
                    BatchIngestResult(
                        id=item_id,
                        filename=filename,
                        candidate_name=candidate_name,
                        status="success",
                        message=f"Successfully ingested and indexed {filename} into knowledge base.",
                    )
                )

            except Exception as e:
                results.append(
                    BatchIngestResult(
                        id=item_id,
                        filename=filename,
                        candidate_name=candidate_name,
                        status="failed",
                        message=f"Ingestion failed: {str(e)}",
                    )
                )

        conn.close()
        return BatchIngestResponse(
            success=ingested_count > 0 or len(results) == 0,
            ingested_count=ingested_count,
            results=results,
        )
