import os
import pandas as pd
from unstructured.partition.auto import partition
import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parents[1])
)

def detect_header_row(raw_df: pd.DataFrame) -> int:
    """
    Finds the actual table header row in a dataframe.
    Looks for candidate/recruitment related keywords in the first 15 rows.
    Defaults to 0 (top row) if no preamble/title row is detected.
    """
    header_keywords = {
        "candidate", "candidate_name", "candidate_id", "full_name", 
        "name", "applicant", "job_title", "role", "email", 
        "skills", "technical_skills", "experience", "resume"
    }

    for index, row in raw_df.head(15).iterrows():
        row_values = [
            str(v).strip().lower()
            for v in row.tolist()
            if pd.notna(v)
        ]
        if any(any(kw in val for kw in header_keywords) for val in row_values):
            return index

    return 0


def extract_tabular_chunks(df: pd.DataFrame) -> list:
    """
    Converts dataframe rows into structured text chunks for RAG embedding.
    Intelligently handles various candidate/name column names and filters empty/summary rows.
    """
    df.columns = [str(c).strip() for c in df.columns]

    candidate_col = None
    for col in df.columns:
        clean = col.lower().replace("_", " ").strip()
        if clean in ["candidate", "candidate name", "full name", "fullname", "name", "applicant"]:
            candidate_col = col
            break

    extracted_chunks = []
    for _, row in df.iterrows():
        if row.dropna().empty:
            continue

        if candidate_col and pd.notna(row.get(candidate_col)):
            cand_str = str(row.get(candidate_col)).strip()
            if not cand_str or cand_str.lower().startswith(("average", "total", "summary", "count")):
                continue

        row_parts = []
        for col, val in row.items():
            if pd.notna(val) and str(val).strip() != "":
                row_parts.append(f"{col}: {val}")

        row_text = ", ".join(row_parts)
        if row_text.strip():
            extracted_chunks.append(f"Candidate/Row Record: {row_text}")

    return extracted_chunks


def parse_ta_csv(file_obj):
    """
    Parse CSV directly from memory without saving it locally.
    Supports standard CSV headers, arbitrary candidate column names,
    and multi-row preamble/export formats.
    """
    try:
        raw_df = pd.read_csv(file_obj, header=None)
    except Exception as e:
        raise ValueError(f"Could not read CSV file: {e}")

    if raw_df.empty:
        return []

    header_row = detect_header_row(raw_df)

    file_obj.seek(0)
    try:
        df = pd.read_csv(file_obj, header=header_row)
    except Exception:
        file_obj.seek(0)
        df = pd.read_csv(file_obj, header=0)

    extracted_chunks = extract_tabular_chunks(df)
    print(f"Successfully extracted {len(extracted_chunks)} CSV chunks.")
    return extracted_chunks

import re

##extract candidate name and email from resume text
import re


def extract_candidate_metadata(text: str):
    """
    Extract candidate name and email from resume text.
    """

    candidate_name = ""
    email = ""

    # Extract email if the resume contains one
    email_match = re.search(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        text
    )
    if email_match:
        email = email_match.group(0).strip()

    # Extract candidate name from:
    # 1. Explicit label (Name: ... or Candidate Name: ...)
    name_match = re.search(
        r"(?im)^(?:candidate\s+name|name)\s*[:\-]\s*(.+)$",
        text
    )
    if name_match:
        candidate_name = name_match.group(1).strip()
    else:
        # 2. Fallback: First prominent line containing a 2-4 word full name
        for line in text.splitlines():
            clean = line.strip()
            if not clean or "@" in clean or "http" in clean.lower():
                continue
            if any(kw in clean.lower() for kw in ["resume", "curriculum", "cv", "profile", "contact", "summary"]):
                continue
            words = clean.split()
            if 2 <= len(words) <= 4 and all(w.replace(".", "").isalpha() for w in words):
                candidate_name = clean
                break

    return {
        "candidate_name": candidate_name,
        "email": email
    }


def parse_ta_document(file_path: str):
    """
    Parses Talent Acquisition documents
    (Resumes, JDs, Spreadsheets)
    using Unstructured and Pandas based on file extensions.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"TA Document not found: {file_path}"
        )

    file_ext = os.path.splitext(file_path)[1].lower()

    print(
        f"Processing TA file [{file_ext}]: {file_path}..."
    )

    extracted_chunks = []

    # =====================================================
    # CSV FILES
    # =====================================================

    if file_ext == ".csv":
        raw_df = pd.read_csv(file_path, header=None)
        header_row = detect_header_row(raw_df)
        try:
            df = pd.read_csv(file_path, header=header_row)
        except Exception:
            df = pd.read_csv(file_path, header=0)

        extracted_chunks.extend(extract_tabular_chunks(df))

    # =====================================================
    # EXCEL FILES
    # =====================================================

    elif file_ext in [".xlsx", ".xls"]:
        raw_df = pd.read_excel(file_path, header=None)
        header_row = detect_header_row(raw_df)
        try:
            df = pd.read_excel(file_path, header=header_row)
        except Exception:
            df = pd.read_excel(file_path, header=0)

        extracted_chunks.extend(extract_tabular_chunks(df))

    # =====================================================
    # PDF / DOCX / TXT / OTHER DOCUMENTS
    # =====================================================

    else:

        elements = partition(
            filename=file_path
        )

        text_blocks = [
            str(el).strip()
            for el in elements
            if str(el).strip()
        ]

        # Combine small Unstructured elements
        # into larger chunks
        current_chunk = ""

        for block in text_blocks:

            if len(current_chunk) + len(block) <= 1000:

                current_chunk += block + "\n"

            else:

                extracted_chunks.append(
                    current_chunk.strip()
                )

                current_chunk = block + "\n"
        #for final chunk
        if current_chunk.strip():

            extracted_chunks.append(
                current_chunk.strip()
            )

    print(
        f"Successfully extracted "
        f"{len(extracted_chunks)} text blocks/chunks."
    )

    return extracted_chunks


if __name__ == "__main__":

    print(
        "TA Document Parser module loaded successfully."
    )
