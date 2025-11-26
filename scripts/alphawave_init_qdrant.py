from qdrant_client import QdrantClient

QDRANT_URL = "http://localhost:6333"
VECTOR_SIZE = 1536
DISTANCE = "Cosine"

collections = [
    # Shared domain collections
    "business_alphawave",
    "design_guidelines",
]

# Per-user collections will be created dynamically as needed, but you can seed examples here
example_users = [
    "glen",
]

for user in example_users:
    collections.append(f"nicole_core_{user}")
    collections.append(f"document_repo_{user}")


def main():
    client = QdrantClient(url=QDRANT_URL)
    for name in collections:
        try:
            client.create_collection(
                collection_name=name,
                vectors_config={"size": VECTOR_SIZE, "distance": DISTANCE},
            )
            print(f"Created collection: {name}")
        except Exception as e:
            print(f"Skipped {name}: {e}")


if __name__ == "__main__":
    main()
