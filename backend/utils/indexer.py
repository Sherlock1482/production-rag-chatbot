import os
import hashlib

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from langchain_huggingface import HuggingFaceEmbeddings

from utils.parser import parse_ta_document, extract_candidate_metadata


# 1. Initialize Embedding Model
print("Loading LangChain embedding model (BAAI/bge-large-en-v1.5)...")

embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-large-en-v1.5",
    encode_kwargs={"normalize_embeddings": True},
)


# 2. Initialize Qdrant Client
QDRANT_URL = os.getenv(
    "QDRANT_URL",
    "http://localhost:6333"
)

client = QdrantClient(url=QDRANT_URL)

COLLECTION_NAME = "ta_documents"


def init_vector_db():
    """
    Initializes the Qdrant collection if it doesn't already exist.
    """

    collections = client.get_collections().collections

    exists = any(
        col.name == COLLECTION_NAME
        for col in collections
    )

    if not exists:

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=1024,
                distance=Distance.COSINE
            )
        )

        print(
            f"Created Qdrant collection: {COLLECTION_NAME}"
        )

    else:

        print(
            f"Qdrant collection '{COLLECTION_NAME}' already exists."
        )


def reset_vector_db():
    """
    Deletes and recreates the Qdrant collection.

    Used only when running indexer.py directly
    to remove old/duplicate test data.
    """

    collections = client.get_collections().collections

    exists = any(
        col.name == COLLECTION_NAME
        for col in collections
    )

    if exists:

        client.delete_collection(
            collection_name=COLLECTION_NAME
        )

        print(
            f"Deleted old collection: {COLLECTION_NAME}"
        )

    init_vector_db()


def index_ta_chunks(chunks: list, metadata_source: str):
    """
    Embeds text chunks and upserts them into Qdrant
    with candidate metadata.
    """

    init_vector_db()

    if not chunks:
        print("No chunks to index.")
        return

    print(
        f"Generating embeddings for {len(chunks)} chunks "
        f"from {metadata_source}..."
    )

    # Combine all chunks so candidate metadata
    # is extracted only once.
    full_text = "\n".join(chunks)

    metadata = extract_candidate_metadata(full_text)

    candidate_name = metadata.get(
        "candidate_name",
        ""
    )

    email = metadata.get(
        "email",
        ""
    )

    print(f"Candidate: {candidate_name}")
    print(f"Email: {email}")

    # Generate embeddings
    embeddings = embedding_model.embed_documents(chunks)

    points = []

    for idx, (chunk, vector) in enumerate(
        zip(chunks, embeddings)
    ):

        # Create a deterministic ID.
        #
        # Same source + same chunk index
        # will always produce the same ID.
        point_key = f"{metadata_source}_{idx}"

        point_id = int(
            hashlib.sha256(
                point_key.encode()
            ).hexdigest()[:16],
            16
        )

        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "text": chunk,
                    "source": metadata_source,
                    "candidate_name": candidate_name,
                    "email": email,
                },
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )

    print(
        f"Successfully indexed {len(points)} chunks into Qdrant!"
    )


if __name__ == "__main__":

    # Reset old test data when running this file directly.
    #
    # IMPORTANT:
    # This does NOT affect the /upload API because
    # reset_vector_db() is only called here.
    reset_vector_db()

    data_dir = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data"
    )

    resumes = [
        os.path.join(
            data_dir,
            "resumes",
            "raj.txt"
        ),
        os.path.join(
            data_dir,
            "resumes",
            "priya.txt"
        ),
        os.path.join(
            data_dir,
            "resumes",
            "arjun.txt"
        )
    ]

    for file_path in resumes:

        chunks = parse_ta_document(
            file_path
        )

        index_ta_chunks(
            chunks,
            os.path.basename(file_path)
        )