from qdrant_client import QdrantClient

from core.config import settings

COLLECTION_NAME = "health_documents"


def get_qdrant_client() -> QdrantClient:
    # https=False — self-hosted Qdrant has no TLS; the client defaults to
    # https=True whenever an api_key is set (assumes Qdrant Cloud) unless told otherwise.
    return QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        api_key=settings.qdrant_api_key or None,
        https=False,
    )
