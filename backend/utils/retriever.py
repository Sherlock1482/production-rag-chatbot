import os
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

# 1. Initialize Embedding Model & Qdrant Client
print("Loading embedding model for retrieval...")
embedding_model = SentenceTransformer("BAAI/bge-large-en-v1.5")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
client = QdrantClient(url=QDRANT_URL)
COLLECTION_NAME = "ta_documents"

# 2. Initialize BGE-Reranker-Large
print("Loading BGE-Reranker-Large model...")
reranker_model_name = "BAAI/bge-reranker-large"
reranker_tokenizer = AutoTokenizer.from_pretrained(reranker_model_name)
reranker_model = AutoModelForSequenceClassification.from_pretrained(reranker_model_name)
reranker_model.eval() # Set to evaluation mode

def search_and_rerank(query: str, top_k: int = 5, top_n: int = 3):
    """
    Step 1: Retrieve top_k chunks from Qdrant vector database.
    Step 2: Rerank them using BGE-Reranker-Large to get the top_n precise contexts.
    """
    print(f"\n--- Processing Query: '{query}' ---")
    
    # --- STEP 1: Vector Retrieval (Qdrant) ---
    query_vector = embedding_model.encode(query, normalize_embeddings=True).tolist()
    
    search_results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k
    ).points
    
    if not search_results:
        print("No matching documents found in Qdrant.")
        return []

    # Extract text and metadata payloads
    retrieved_docs = []
    for result in search_results:
        retrieved_docs.append({
            "text": result.payload.get("text"),
            "source": result.payload.get("source"),
            "initial_score": result.score
        })
    
    print(f"Retrieved {len(retrieved_docs)} raw chunks from Qdrant.")

    # --- STEP 2: Precision Reranking (BGE-Reranker-Large) ---
    # Pair the query with each retrieved document text
    pairs = [[query, doc["text"]] for doc in retrieved_docs]
    
    with torch.no_grad():
        inputs = reranker_tokenizer(
            pairs, 
            padding=True, 
            truncation=True, 
            return_tensors='pt', 
            max_length=512
        )
        scores = reranker_model(**inputs).logits.squeeze(-1).float().tolist()
        
    # Handle single result edge case where output might be a float instead of a list
    if isinstance(scores, float):
        scores = [scores]

    # Attach rerank scores to documents
    for doc, score in zip(retrieved_docs, scores):
        doc["rerank_score"] = score

    # Sort documents by rerank score in descending order
    ranked_docs = sorted(retrieved_docs, key=lambda x: x["rerank_score"], reverse=True)
    
    # Keep only the top_n best results
    final_top_n = ranked_docs[:top_n]
    
    print(f"Reranked and filtered down to top {len(final_top_n)} contexts for the LLM.")
    return final_top_n

if __name__ == "__main__":
    print("Retriever module loaded successfully.")