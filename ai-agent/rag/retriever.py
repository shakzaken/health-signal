from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from ingestion.embedder import Embedder
from rag.qdrant_client import COLLECTION_NAME

DEFAULT_USER_ID = "default"
TOP_K = 5


class Retriever:
    """
    Semantic retrieval from Qdrant.
    Always scopes results to a specific user — user isolation is not a RAG problem.
    Optionally narrows by document_type for targeted queries.
    """

    def __init__(self, client: QdrantClient, embedder: Embedder) -> None:
        self._client = client
        self._embedder = embedder

    def retrieve(
        self,
        query: str,
        user_id: str = DEFAULT_USER_ID,
        document_type: str | None = None,
        top_k: int = TOP_K,
    ) -> list[dict]:
        """Embed query and return the top-k most relevant chunks from Qdrant."""
        query_vector = self._embedder.embed([query])[0]

        must_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]
        if document_type:
            must_conditions.append(
                FieldCondition(key="document_type", match=MatchValue(value=document_type))
            )

        response = self._client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
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
            for hit in response.points
        ]
