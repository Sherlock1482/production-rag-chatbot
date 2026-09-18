import os
from dotenv import load_dotenv

load_dotenv()


# Configurable threshold
RERANKER_THRESHOLD = float(
    os.getenv("RERANKER_THRESHOLD", "-5.0")
)


def check_evidence_guardrail(relevant_docs: list) -> bool:
    """
    Checks whether the retrieved documents contain
    sufficient evidence to answer the user's question.

    Returns:
        True  -> enough evidence
        False -> insufficient evidence
    """

    if not relevant_docs:
        return False

    scores = [
        doc.get("rerank_score")
        for doc in relevant_docs
        if doc.get("rerank_score") is not None
    ]

    if not scores:
        return False

    best_score = max(scores)

    print(f"Best reranker score: {best_score}")
    print(f"Evidence threshold: {RERANKER_THRESHOLD}")


    return best_score >= RERANKER_THRESHOLD