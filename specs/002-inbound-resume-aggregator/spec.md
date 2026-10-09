# Spec 002: Inbound Resume Aggregator (Email & LinkedIn MCP Integration with Recruiter Notification Drawer)

## 1. Problem Statement & Scope
Recruiters receive resumes across disparate inbound communication channels—primarily corporate email (Gmail/Outlook) and LinkedIn InMail/job applicant alerts. 

Currently, recruiters must manually download attachments from their email or LinkedIn, switch to the TA Copilot, and upload them one by one. This causes friction, delays in candidate screening, and duplicate entries when candidates apply multiple times or through multiple channels.

### Objectives
1. **Inbound Channel Aggregation via FastMCP**: Connect an MCP tool capable of reading candidate applications with attached resumes from connected email (Gmail/IMAP) and LinkedIn notifications, with hybrid support (realistic inbox generator for instant validation + `.env` hooks for live credentials).
2. **Persistent Pending Queue in SQLite**: Store unreviewed resumes in a dedicated `pending_resumes` table in `ta_interviews.db` so state is preserved across server restarts and browser refreshes.
3. **Automated Duplicate & Redundancy Detection**: Compute MD5/SHA256 hashes and candidate name matches against existing documents in Qdrant and SQLite to tag candidates with `is_duplicate: true` and a clear visual warning badge (`⚠️ Possible Duplicate`).
4. **Recruiter Notification Bell & Triage Drawer in Frontend**:
   - An unread counter badge on a topbar Bell icon (`🔔 3`).
   - A slide-over notification drawer displaying candidate cards, source tags (e.g. `LinkedIn`, `Gmail`), timestamps, and duplicate warning badges.
   - **Triage Actions**:
     - **Ingest All** (or ingest selected with multi-select checkboxes).
     - **Deny / Remove** (per-candidate deny button or bulk "Deny Selected") to purge redundant/spam resumes before they touch Qdrant or Neo4j.
5. **Human-in-the-Loop (HITL) Adherence**: Under Constitution Principle 5, no resume is indexed into Qdrant or Neo4j until explicitly approved/ingested by the recruiter.

---

## 2. Architectural Flow

```
┌────────────────────────────────────────────────────────┐
│ External Channels (Gmail / Outlook / LinkedIn Alerts)   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ FastMCP Tool: fetch_inbound_resumes                    │
│ - Inspects inbox attachments (.pdf, .docx)             │
│ - Extracts sender, candidate name, date, file buffer   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Backend Inbound Resume Manager (SQLite: pending_resumes)│
│ - Stores metadata & file content in staging            │
│ - Computes duplicate hash & name matches against DB    │
│ - Status: `pending`, `ingested`, or `denied`           │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Next.js Frontend Topbar Notification Bell              │
│ - Shows badge count: 🔔 (3)                            │
│ - Recruiter clicks bell -> Opens Triage Drawer         │
└─────────────┬────────────────────────────┬─────────────┘
              │                            │
   [ Recruiter clicks "Ingest" ]  [ Recruiter clicks "Deny / Remove" ]
              │                            │
              ▼                            ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│ Batch Ingest Pipeline     │ │ Purge from Pending Queue  │
│ - Parse text (PDF/DOCX)   │ │ - Status -> `denied`      │
│ - Index chunks to Qdrant  │ │ - Staging file removed    │
│ - Extract nodes to Neo4j  │ │ - Never touches Qdrant    │
│ - Status -> `ingested`    │ └───────────────────────────┘
└───────────────────────────┘
```

---

## 3. Strict Typed Contracts (Pydantic Models)

```python
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class PendingResumeItem(BaseModel):
    id: str = Field(description="Unique UUID for this pending resume item.")
    candidate_name: str = Field(description="Detected or parsed candidate name.")
    email_sender: str = Field(description="Sender email or LinkedIn notification sender.")
    source_channel: str = Field(description="Origin channel: 'LinkedIn', 'Gmail', or 'Outlook'.")
    received_at: str = Field(description="ISO timestamp of when the message/attachment was received.")
    filename: str = Field(description="Filename of the resume attachment (e.g. Alex_Chen_Resume.pdf).")
    filesize_bytes: int = Field(description="Size of the attachment in bytes.")
    file_path: str = Field(description="Path to staged temporary file on disk.")
    status: str = Field(default="pending", description="Status: 'pending', 'ingested', or 'denied'.")
    is_duplicate: bool = Field(default=False, description="True if filename, hash, or candidate name matches existing records.")
    duplicate_reason: Optional[str] = Field(default=None, description="Explanation of why this candidate was flagged as duplicate.")

class PendingResumeResponse(BaseModel):
    total_pending: int
    items: List[PendingResumeItem]

class BatchIngestRequest(BaseModel):
    resume_ids: List[str] = Field(description="List of pending resume item IDs to ingest. Empty list means 'ingest all pending'.")

class BatchIngestResult(BaseModel):
    id: str
    filename: str
    candidate_name: str
    status: str # 'success' or 'failed'
    message: str

class BatchIngestResponse(BaseModel):
    success: bool
    ingested_count: int
    results: List[BatchIngestResult]

class DenyResumeRequest(BaseModel):
    resume_ids: List[str] = Field(description="List of pending resume item IDs to deny/remove.")

class DenyResumeResponse(BaseModel):
    success: bool
    denied_count: int
    message: str
```

---

## 4. REST API Contract (`backend/main.py`)

1. `GET /inbox/pending-resumes`:
   - Returns all items with status `pending`.
2. `POST /inbox/sync`:
   - Triggers FastMCP tool `fetch_inbound_resumes` to poll external channels, persists newly discovered items in SQLite, checks duplicates, and returns updated pending count.
3. `POST /inbox/ingest`:
   - Accepts `BatchIngestRequest`. Ingests the specified resume files (or all pending if list is empty) through the existing `parse_ta_document` and `index_ta_chunks` pipeline, marks them `ingested`, and updates Neo4j/Qdrant.
4. `POST /inbox/deny`:
   - Accepts `DenyResumeRequest`. Marks the specified resume files as `denied` and purges their staging files.

---

## 5. Acceptance Criteria (BDD Given-When-Then)

### Scenario 1: Notification badge and drawer display
- **Given** 3 pending resumes exist in the database from Gmail and LinkedIn,
- **When** the recruiter loads the frontend,
- **Then** the notification bell shows badge counter `3`, and clicking it displays the 3 candidate cards with source tags and details.

### Scenario 2: Duplicate detection warning
- **Given** a candidate named "Alex Chen" already has an indexed resume in Qdrant,
- **When** a new email from LinkedIn arrives with "Alex_Chen_Resume.pdf",
- **Then** the pending item is marked with `is_duplicate: true` and displays `⚠️ Possible Duplicate: Existing candidate in database`.

### Scenario 3: Recruiter batch ingests all resumes
- **Given** 3 pending resumes in the drawer,
- **When** the recruiter clicks "Ingest All",
- **Then** the backend processes and indexes all 3 documents into Qdrant, marks their status as `ingested`, and the notification badge updates to `0`.

### Scenario 4: Recruiter denies/removes redundant resume
- **Given** a duplicate resume in the pending list,
- **When** the recruiter clicks "Deny / Remove" on that candidate card,
- **Then** the candidate is removed from the pending list and marked `denied`, and neither Qdrant nor Neo4j indexes the document.
