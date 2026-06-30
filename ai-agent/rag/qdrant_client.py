from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from core.config import settings

COLLECTION_NAME = "health_documents"
VECTOR_SIZE = 4096  # qwen/qwen3-embedding-8b


def get_qdrant_client() -> QdrantClient:
    # https=False — self-hosted Qdrant has no TLS; the client defaults to
    # https=True whenever an api_key is set (assumes Qdrant Cloud) unless told otherwise.
    return QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        api_key=settings.qdrant_api_key or None,
        https=False,
    )


def ensure_collection(client: QdrantClient) -> None:
    """Create the health_documents collection if it does not exist."""
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
