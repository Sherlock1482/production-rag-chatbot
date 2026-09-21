import os
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from utils.parser import parse_ta_document


# 1. Initialize Embedding Model (BAAI/bge-large-en-v1.5)
print("Loading embedding model (BAAI/bge-large-en-v1.5)...")
embedding_model = SentenceTransformer("BAAI/bge-large-en-v1.5")

# 2. Initialize Qdrant Client (Connected locally or via Docker)
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
client = QdrantClient(url=QDRANT_URL)

COLLECTION_NAME = "ta_documents"

def init_vector_db():
    """Initializes the Qdrant collection if it doesn't already exist."""
    collections = client.get_collections().collections
    exists = any(col.name == COLLECTION_NAME for col in collections)
    
    if not exists:
        # BGE-large-en-v1.5 produces vectors of dimension 1024
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
        )
        print(f"Created Qdrant collection: {COLLECTION_NAME}")
    else:
        print(f"Qdrant collection '{COLLECTION_NAME}' already exists.")

def index_ta_chunks(chunks: list, metadata_source: str):
    """
    Embeds text chunks and upserts them into Qdrant with source metadata.
    """
    init_vector_db()
    
    if not chunks:
        print("No chunks to index.")
        return

    print(f"Generating embeddings for {len(chunks)} chunks from {metadata_source}...")
    
    # Generate dense vector embeddings
    embeddings = embedding_model.encode(chunks, normalize_embeddings=True)
    
    points = []
    for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
        point_id = hash(f"{metadata_source}_{idx}") % (2**63) # Generate a unique numeric ID
        points.append(
            PointStruct(
                id=abs(point_id),
                vector=vector.tolist(),
                payload={
                    "text": chunk,
                    "source": metadata_source
                }
            )
        )
    
    # Upload points to Qdrant
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    print(f"Successfully indexed {len(points)} chunks into Qdrant!")
if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    resumes = [
        os.path.join(data_dir, "resumes", "raj.txt"),
        os.path.join(data_dir, "resumes", "priya.txt"),
        os.path.join(data_dir, "resumes", "arjun.txt")
    ]

    for file_path in resumes:
        chunks = parse_ta_document(file_path)

        index_ta_chunks(
            chunks,
            os.path.basename(file_path)
        )