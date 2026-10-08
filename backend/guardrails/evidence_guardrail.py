import os
from dotenv import load_dotenv
from langfuse import get_client


# Load environment variables
load_dotenv()


# ============================================================
# Langfuse
# ============================================================

langfuse = get_client()


# ============================================================
# Configurable Threshold
# ============================================================

RERANKER_THRESHOLD = float(
    os.getenv(
        "RERANKER_THRESHOLD",
        "-5.0"
    )
)


# ============================================================
# Evidence Guardrail
# ============================================================

def check_evidence_guardrail(
    relevant_docs: list,
    has_graph_evidence: bool = False
) -> bool:
    """
    Checks whether the retrieved documents or Knowledge Graph contain
    sufficient evidence to answer the user's question.

    Returns:
        True  -> enough evidence
        False -> insufficient evidence
    """

    # ========================================================
    # Langfuse Observation
    # ========================================================

    with langfuse.start_as_current_observation(
        as_type="span",
        name="evidence-guardrail",
        input={
            "documents_received": len(
                relevant_docs
            ),
            "threshold": RERANKER_THRESHOLD,
            "has_graph_evidence": has_graph_evidence
        }
    ) as guardrail_trace:

        # ----------------------------------------------------
        # Knowledge Graph verified evidence
        # ----------------------------------------------------

        if has_graph_evidence:

            guardrail_trace.update(
                output={
                    "allowed": True,
                    "reason": "Knowledge Graph provided verified candidate evidence",
                    "has_graph_evidence": True
                }
            )

            return True

        # ----------------------------------------------------
        # No documents
        # ----------------------------------------------------

        if not relevant_docs:

            guardrail_trace.update(
                output={
                    "allowed": False,
                    "reason": "No relevant documents"
                }
            )

            return False

        # ----------------------------------------------------
        # Get reranker scores
        # ----------------------------------------------------

        scores = [
            doc.get("rerank_score")
            for doc in relevant_docs
            if doc.get("rerank_score") is not None
        ]

        # ----------------------------------------------------
        # No scores
        # ----------------------------------------------------

        if not scores:

            guardrail_trace.update(
                output={
                    "allowed": False,
                    "reason": "No reranker scores"
                }
            )

            return False

        # ----------------------------------------------------
        # Find best score
        # ----------------------------------------------------

        best_score = max(scores)

        print(
            f"Best reranker score: {best_score}"
        )

        print(
            f"Evidence threshold: "
            f"{RERANKER_THRESHOLD}"
        )

        # ----------------------------------------------------
        # Evidence decision
        # ----------------------------------------------------

        allowed = (
            best_score >= RERANKER_THRESHOLD
        )

        # ----------------------------------------------------
        # Record result in Langfuse
        # ----------------------------------------------------

        guardrail_trace.update(
            output={
                "allowed": allowed,
                "best_score": best_score,
                "threshold": RERANKER_THRESHOLD,
                "scores": scores
            }
        )

        return allowed