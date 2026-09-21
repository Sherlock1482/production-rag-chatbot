import os

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

from langfuse import get_client


# ============================================================
# Langfuse
# ============================================================

langfuse = get_client()


# ============================================================
# 1. Initialize Embedding Model & Qdrant Client
# ============================================================

print("Loading embedding model for retrieval...")

embedding_model = SentenceTransformer(
    "BAAI/bge-large-en-v1.5"
)

QDRANT_URL = os.getenv(
    "QDRANT_URL",
    "http://localhost:6333"
)

client = QdrantClient(
    url=QDRANT_URL
)

COLLECTION_NAME = "ta_documents"


# ============================================================
# 2. Initialize BGE-Reranker-Large
# ============================================================

print("Loading BGE-Reranker-Large model...")

reranker_model_name = (
    "BAAI/bge-reranker-large"
)

reranker_tokenizer = (
    AutoTokenizer.from_pretrained(
        reranker_model_name
    )
)

reranker_model = (
    AutoModelForSequenceClassification
    .from_pretrained(
        reranker_model_name
    )
)

# Set reranker to evaluation mode
reranker_model.eval()


# ============================================================
# Search + Rerank
# ============================================================

def search_and_rerank(
    query: str,
    top_k: int = 5,
    top_n: int = 3
):
    """
    Step 1:
        Retrieve top_k chunks from Qdrant.

    Step 2:
        Rerank retrieved chunks using
        BGE-Reranker-Large.

    Step 3:
        Return top_n documents.
    """

    print(
        f"\n--- Processing Query: '{query}' ---"
    )

    # ========================================================
    # STEP 1: Vector Retrieval
    # ========================================================

    with langfuse.start_as_current_observation(
        as_type="span",
        name="qdrant-retrieval",
        input={
            "query": query,
            "top_k": top_k
        }
    ) as retrieval_trace:

        # Generate query embedding
        query_vector = (
            embedding_model
            .encode(
                query,
                normalize_embeddings=True
            )
            .tolist()
        )

        # Search Qdrant
        search_results = (
            client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                limit=top_k
            ).points
        )

        # No results
        if not search_results:

            print(
                "No matching documents found in Qdrant."
            )

            retrieval_trace.update(
                output={
                    "retrieved_documents": 0
                }
            )

            return []

        # ----------------------------------------------------
        # Extract text and metadata
        # ----------------------------------------------------

        retrieved_docs = []

        for result in search_results:

            retrieved_docs.append({
                "text": result.payload.get(
                    "text"
                ),
                "source": result.payload.get(
                    "source"
                ),
                "initial_score": result.score
            })

        print(
            f"Retrieved {len(retrieved_docs)} "
            "raw chunks from Qdrant."
        )

        # Record retrieval result in Langfuse
        retrieval_trace.update(
            output={
                "retrieved_documents": len(
                    retrieved_docs
                ),
                "documents": [
                    {
                        "source": doc["source"],
                        "score": doc["initial_score"]
                    }
                    for doc in retrieved_docs
                ]
            }
        )


    # ========================================================
    # STEP 2: Precision Reranking
    # ========================================================

    with langfuse.start_as_current_observation(
        as_type="span",
        name="bge-reranking",
        input={
            "query": query,
            "documents_received": len(
                retrieved_docs
            ),
            "top_n": top_n
        }
    ) as rerank_trace:

        # Pair query with each document
        pairs = [
            [query, doc["text"]]
            for doc in retrieved_docs
        ]

        # Run BGE reranker
        with torch.no_grad():

            inputs = reranker_tokenizer(
                pairs,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=512
            )

            scores = (
                reranker_model(
                    **inputs
                )
                .logits
                .squeeze(-1)
                .float()
                .tolist()
            )

        # Handle single-result edge case
        if isinstance(scores, float):

            scores = [scores]

        # ----------------------------------------------------
        # Attach rerank scores
        # ----------------------------------------------------

        for doc, score in zip(
            retrieved_docs,
            scores
        ):

            doc["rerank_score"] = score

        # ----------------------------------------------------
        # Sort by rerank score
        # ----------------------------------------------------

        ranked_docs = sorted(
            retrieved_docs,
            key=lambda x: x["rerank_score"],
            reverse=True
        )

        # ----------------------------------------------------
        # Keep top_n
        # ----------------------------------------------------

        final_top_n = ranked_docs[:top_n]

        # Record reranking result in Langfuse
        rerank_trace.update(
            output={
                "reranked_documents": len(
                    ranked_docs
                ),
                "selected_documents": [
                    {
                        "source": doc["source"],
                        "initial_score": doc[
                            "initial_score"
                        ],
                        "rerank_score": doc[
                            "rerank_score"
                        ]
                    }
                    for doc in final_top_n
                ]
            }
        )

    return final_top_n


# ============================================================
# Direct Test
# ============================================================

if __name__ == "__main__":

    print(
        "Retriever module loaded successfully."
    )