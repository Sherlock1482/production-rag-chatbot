import os
import pandas as pd
from unstructured.partition.auto import partition
import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parents[1])
)

def parse_ta_document(file_path: str):
    """
    Parses Talent Acquisition documents (Resumes, JDs, Spreadsheets)
    using Unstructured and Pandas based on file extensions.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"TA Document not found: {file_path}")

    file_ext = os.path.splitext(file_path)[1].lower()

    print(f"Processing TA file [{file_ext}]: {file_path}...")

    extracted_chunks = []

    # Special handling for Excel spreadsheets
    if file_ext in [".xlsx", ".xls"]:

        df = pd.read_excel(file_path)

        # Convert rows into structured text summaries
        for index, row in df.iterrows():

            row_text = ", ".join(
                [
                    f"{col}: {val}"
                    for col, val in row.items()
                    if pd.notna(val)
                ]
            )

            extracted_chunks.append(
                f"Candidate/Row Record: {row_text}"
            )

    # Standard handling for PDFs, Word Docs, and text files
    else:

        elements = partition(filename=file_path)

        text_blocks = [
            str(el).strip()
            for el in elements
            if str(el).strip()
        ]

        # Combine small Unstructured elements into larger chunks
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
        f"Successfully extracted {len(extracted_chunks)} text blocks/chunks."
    )

    return extracted_chunks


if __name__ == "__main__":
    print("TA Document Parser module loaded successfully.")