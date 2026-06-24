from qdrant_client import QdrantClient
from qdrant_client.models import DatetimeRange, FieldCondition, Filter, MatchValue, Range

from ingestion.embedder import Embedder
from rag.qdrant_client import COLLECTION_NAME

TOP_K = 8


class Retriever:
    """
    Semantic retrieval from Qdrant.
    Always scopes results to a specific user — user isolation is not a RAG problem.
    Optionally narrows by document_type and/or source_date range for targeted queries.
    """

    def __init__(self, client: QdrantClient, embedder: Embedder) -> None:
        self._client = client
        self._embedder = embedder

    async def retrieve(
        self,
        query: str,
        user_id: str = "",
        document_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        top_k: int = TOP_K,
    ) -> list[dict]:
        """
        Embed query and return the top-k most relevant chunks from Qdrant.

        date_from / date_to are ISO date strings (YYYY-MM-DD).
        When provided they restrict results to chunks whose source_date falls
        within the given range — enabling time-aware retrieval.
        """
        query_vector = (await self._embedder.embed([query]))[0]

        must_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]
        if document_type:
            must_conditions.append(
                FieldCondition(key="document_type", match=MatchValue(value=document_type))
            )
        if date_from or date_to:
            range_kwargs: dict = {}
            if date_from:
                range_kwargs["gte"] = date_from
            if date_to:
                range_kwargs["lte"] = date_to
            must_conditions.append(
                FieldCondition(key="source_date", range=Range(**range_kwargs))
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
