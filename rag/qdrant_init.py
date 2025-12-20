import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

def ensure_collection(name="osiptel_news", dim=1024):
    local_path = os.getenv("QDRANT_LOCAL_PATH")  # p.ej. "./qdrant_data"
    url = os.getenv("QDRANT_URL")

    if local_path:
        client = QdrantClient(path=local_path)     # persistente en disco
    elif url:
        client = QdrantClient(url=url)             # servidor remoto/local
    else:
        client = QdrantClient(":memory:")          # rápido para pruebas

    if not client.collection_exists(name):
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
    return client

if __name__ == "__main__":
    ensure_collection()
    print("Qdrant listo.")