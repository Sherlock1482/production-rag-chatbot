import re
from pathlib import Path

from utils.context_manager import is_valid_candidate_name


def extract_candidate_metadata_from_text(text: str):
    """
    Extract candidate name and email from text without importing heavy external libraries.
    """
    candidate_name = ""
    email = ""

    email_match = re.search(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        text,
    )
    if email_match:
        email = email_match.group(0).strip()

    name_match = re.search(
        r"(?im)^(?:candidate\s+name|name)\s*[:\-]\s*(.+)$",
        text,
    )
    if name_match:
        candidate_name = name_match.group(1).strip()
    else:
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
        "email": email,
    }


def normalize_text(text: str) -> str:
    return " ".join(
        re.sub(r"[^a-z0-9]+", " ", text.casefold()).split()
    )


def resolve_candidate(candidate_name: str):
    """
    Resolve a candidate name using local resumes and Qdrant candidate metadata.
    Returns candidate details if an exact normalized name match is found.
    """
    if not candidate_name or not is_valid_candidate_name(candidate_name):
        return None

    requested_name = normalize_text(candidate_name)
    resumes_dir = Path(__file__).resolve().parents[1] / "data" / "resumes"

    # Use resume metadata when a document has not been indexed yet.
    if resumes_dir.exists():
        for resume_path in resumes_dir.glob("*.txt"):
            try:
                metadata = extract_candidate_metadata_from_text(
                    resume_path.read_text(encoding="utf-8")
                )
                stored_name = metadata.get("candidate_name", "")

                if (
                    stored_name
                    and (
                        requested_name == normalize_text(stored_name)
                        or requested_name in normalize_text(stored_name)
                        or normalize_text(stored_name) in requested_name
                    )
                ):
                    return {
                        "candidate_name": stored_name,
                        "email": metadata.get("email", ""),
                        "source": resume_path.name,
                    }
            except Exception as read_err:
                print(f"Warning: could not read resume {resume_path}: {read_err}")

    # Lazy-load vector indexer only when candidate not resolved from local resumes
    try:
        from utils.indexer import client, embedding_model, COLLECTION_NAME
        if embedding_model is not None and client is not None:
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
                    if stored_name and is_valid_candidate_name(stored_name) and (
                        requested_name in normalize_text(stored_name) or normalize_text(stored_name) in requested_name
                    ):
                        resolved_name = stored_name
                    else:
                        resolved_name = candidate_name.title()

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
    except Exception as qdrant_err:
        print(f"Warning: vector candidate lookup failed: {qdrant_err}")

    return None