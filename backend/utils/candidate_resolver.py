import re
from pathlib import Path

from utils.indexer import client, embedding_model, COLLECTION_NAME
from utils.parser import extract_candidate_metadata


def normalize_text(text: str) -> str:
    return " ".join(
        re.sub(r"[^a-z0-9]+", " ", text.casefold()).split()
    )


def resolve_candidate(candidate_name: str):
    """
    Resolve a candidate name using Qdrant candidate metadata.
    Returns candidate details if an exact normalized name match is found.
    """

    requested_name = normalize_text(candidate_name)
    resumes_dir = Path(__file__).resolve().parents[1] / "data" / "resumes"

    # Use resume metadata when a document has not been indexed yet.
    if resumes_dir.exists():
        for resume_path in resumes_dir.glob("*.txt"):
            metadata = extract_candidate_metadata(
                resume_path.read_text(encoding="utf-8")
            )
            stored_name = metadata.get("candidate_name", "")

            if (
                requested_name == normalize_text(stored_name)
                or requested_name in normalize_text(stored_name)
            ):
                return {
                    "candidate_name": stored_name,
                    "email": metadata.get("email", ""),
                    "source": resume_path.name,
                }

    query_vector = embedding_model.embed_query(candidate_name)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=5,
        with_payload=True,
    ).points

    for result in results:
        payload = result.payload or {}

        stored_name = payload.get("candidate_name", "")
        source_name = payload.get("source", "")
        doc_text = payload.get("text", "")

        matched = False
        if stored_name and (
            normalize_text(stored_name) == requested_name
            or requested_name in normalize_text(stored_name)
        ):
            matched = True
        elif source_name and requested_name in normalize_text(source_name):
            matched = True
        elif doc_text and requested_name in normalize_text(doc_text[:300]):
            matched = True

        if matched:
            resolved_name = stored_name or candidate_name.title()
            print("RESOLVED CANDIDATE:", {
                "candidate_name": resolved_name,
                "email": payload.get("email", ""),
                "source": source_name,
            })

            return {
                "candidate_name": resolved_name,
                "email": payload.get("email", ""),
                "source": source_name,
            }

    return None