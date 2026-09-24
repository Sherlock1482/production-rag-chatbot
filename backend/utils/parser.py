import os
import pandas as pd
from unstructured.partition.auto import partition
import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parents[1])
)

def parse_ta_csv(file_obj):
    """
    Parse CSV directly from memory without saving it locally.
    """

    raw_df = pd.read_csv(
        file_obj,
        header=None
    )

    header_row = None

    for index, row in raw_df.iterrows():

        row_values = [
            str(value).strip()
            for value in row.tolist()
            if pd.notna(value)
        ]

        if "Candidate" in row_values:
            header_row = index
            break

    if header_row is None:
        raise ValueError(
            "Could not find the Candidate table header in CSV file."
        )

    file_obj.seek(0)

    df = pd.read_csv(
        file_obj,
        header=header_row
    )

    extracted_chunks = []

    for _, row in df.iterrows():

        candidate = row.get("Candidate")

        if pd.isna(candidate):
            continue

        candidate = str(candidate).strip()

        if (
            not candidate
            or candidate.lower().startswith("average")
        ):
            continue

        row_text = ", ".join(
            [
                f"{col}: {val}"
                for col, val in row.items()
                if pd.notna(val)
            ]
        )

        if row_text.strip():

            extracted_chunks.append(
                f"Candidate/Row Record: {row_text}"
            )

    print(
        f"Successfully extracted "
        f"{len(extracted_chunks)} CSV chunks."
    )

    return extracted_chunks

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

        raw_df = pd.read_csv(
            file_path,
            header=None
        )

        header_row = None

        # Find the actual Candidate header row
        for index, row in raw_df.iterrows():

            row_values = [
                str(value).strip()
                for value in row.tolist()
                if pd.notna(value)
            ]

            if "Candidate" in row_values:
                header_row = index
                break

        if header_row is None:
            raise ValueError(
                "Could not find the Candidate table header in CSV file."
            )

        # Read CSV again using the detected header
        df = pd.read_csv(
            file_path,
            header=header_row
        )

        # Convert each candidate row into one logical chunk
        for _, row in df.iterrows():

            candidate = row.get("Candidate")

            # Skip empty rows
            if pd.isna(candidate):
                continue

            candidate = str(candidate).strip()

            # Skip empty/summary rows
            if (
                not candidate
                or candidate.lower().startswith("average")
            ):
                continue

            row_text = ", ".join(
                [
                    f"{col}: {val}"
                    for col, val in row.items()
                    if pd.notna(val)
                ]
            )

            if row_text.strip():

                extracted_chunks.append(
                    f"Candidate/Row Record: {row_text}"
                )

    # =====================================================
    # EXCEL FILES
    # =====================================================

    elif file_ext in [".xlsx", ".xls"]:

        # Read Excel without assuming the first row
        # is the header
        raw_df = pd.read_excel(
            file_path,
            header=None
        )

        header_row = None

        # Find the actual Candidate table header
        for index, row in raw_df.iterrows():

            row_values = [
                str(value).strip()
                for value in row.tolist()
                if pd.notna(value)
            ]

            if "Candidate" in row_values:
                header_row = index
                break

        if header_row is None:
            raise ValueError(
                "Could not find the Candidate table header in Excel file."
            )

        # Re-read Excel using detected header
        df = pd.read_excel(
            file_path,
            header=header_row
        )

        # Convert each candidate row into one logical chunk
        for _, row in df.iterrows():

            candidate = row.get("Candidate")

            # Skip empty rows
            if pd.isna(candidate):
                continue

            candidate = str(candidate).strip()

            # Skip empty/summary rows
            if (
                not candidate
                or candidate.lower().startswith("average")
            ):
                continue

            row_text = ", ".join(
                [
                    f"{col}: {val}"
                    for col, val in row.items()
                    if pd.notna(val)
                ]
            )

            if row_text.strip():

                extracted_chunks.append(
                    f"Candidate/Row Record: {row_text}"
                )

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
