import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from rag.qdrant_client import COLLECTION_NAME


def write_chunks(
    client: QdrantClient,
    chunks: list[str],
    vectors: list[list[float]],
    document_id: str,
    user_id: str,
    document_type: str,
    source_date: str | None,
    filename: str,
) -> None:
    """Write embedded chunks with metadata to Qdrant."""
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

    client.upsert(collection_name=COLLECTION_NAME, points=points)
