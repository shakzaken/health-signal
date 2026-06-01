from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from ingestion.embedder import embed_chunks
from rag.qdrant_client import COLLECTION_NAME

DEFAULT_USER_ID = "default"
TOP_K = 5


def retrieve(
    client: QdrantClient,
    query: str,
    user_id: str = DEFAULT_USER_ID,
    document_type: str | None = None,
    top_k: int = TOP_K,
) -> list[dict]:
    """
    Embed query and search Qdrant.
    Always filters by user_id first — user scoping is not a RAG problem.
    Optionally filters by document_type for targeted retrieval.
    """
    query_vector = embed_chunks([query])[0]

    # Build filter: always scope to user, optionally scope to doc type
    must_conditions = [
        FieldCondition(key="user_id", match=MatchValue(value=user_id))
    ]
    if document_type:
        must_conditions.append(
            FieldCondition(key="document_type", match=MatchValue(value=document_type))
        )

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        query_filter=Filter(must=must_conditions),
        limit=top_k,
        with_payload=True,
    )

    return [
        {
            "text": hit.payload.get("text", ""),
            "document_id": hit.payload.get("document_id"),
            "document_type": hit.payload.get("document_type"),
            "source_date": hit.payload.get("source_date"),
            "filename": hit.payload.get("filename"),
            "chunk_index": hit.payload.get("chunk_index"),
            "score": hit.score,
        }
        for hit in results
    ]
