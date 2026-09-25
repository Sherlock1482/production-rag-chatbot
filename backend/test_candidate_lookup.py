from utils.indexer import client, embedding_model, COLLECTION_NAME


query = "Rajuu Sharma"

# Convert query into embedding
query_vector = embedding_model.embed_query(query)

# Search Qdrant
results = client.query_points(
    collection_name=COLLECTION_NAME,
    query=query_vector,
    limit=3,
    with_payload=True,
).points


print("\nCandidate search results:\n")

for result in results:
    payload = result.payload

    print("Candidate:", payload.get("candidate_name"))
    print("Email:", payload.get("email"))
    print("Source:", payload.get("source"))
    print("Score:", result.score)
    print("-" * 40)