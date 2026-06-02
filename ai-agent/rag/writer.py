import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from rag.qdrant_client import COLLECTION_NAME


class QdrantWriter:
    """Writes embedded chunks with metadata into the Qdrant collection."""

    def __init__(self, client: QdrantClient) -> None:
        self._client = client

    def write(
        self,
        chunks: list[str],
        vectors: list[list[float]],
        document_id: str,
        user_id: str,
        document_type: str,
        source_date: str | None,
        filename: str,
    ) -> None:
        """Upsert all chunk vectors into Qdrant with their payload metadata."""
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "text": chunk,
                    "document_id": document_id,
                    "user_id": user_id,
                    "document_type": document_type,
                    "source_date": source_date,
                    "filename": filename,
                    "chunk_index": idx,
                },
            )
            for idx, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]
        self._client.upsert(collection_name=COLLECTION_NAME, points=points)
