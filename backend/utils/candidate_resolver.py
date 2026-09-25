import re

from utils.indexer import client, embedding_model, COLLECTION_NAME


def normalize_text(text: str) -> str:
    return " ".join(
        re.sub(r"[^a-z0-9]+", " ", text.casefold()).split()
    )


def resolve_candidate(candidate_name: str):
    """
    Resolve a candidate name using Qdrant candidate metadata.
    Returns candidate details if an exact normalized name match is found.
    """

    query_vector = embedding_model.embed_query(candidate_name)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=5,
        with_payload=True,
    ).points

    requested_name = normalize_text(candidate_name)

    for result in results:
        payload = result.payload or {}

        stored_name = payload.get("candidate_name", "")

        if (
            normalize_text(stored_name) == requested_name
            or requested_name in normalize_text(stored_name)
        ):

            return {
                "candidate_name": stored_name,
                "email": payload.get("email", ""),
                "source": payload.get("source", ""),
            }

    return None