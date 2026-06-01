import os

from langsmith import traceable

from ingestion.chunker import chunk_text
from ingestion.embedder import embed_chunks
from ingestion.parser import parse_document
from rag.qdrant_client import ensure_collection, get_qdrant_client
from rag.writer import write_chunks

# Default user_id for single-user phase 1
DEFAULT_USER_ID = "default"


@traceable(name="ingestion_pipeline")
async def run_ingestion(
    document_id: str,
    file_path: str,
    document_type: str,
    source_date: str | None,
    filename: str,
) -> dict:
    """
    Deterministic ingestion pipeline:
    parse → chunk → embed → write to Qdrant

    This is NOT an agent — steps are fixed and sequential.
    LangSmith tracing is added for observability.
    """
    try:
        # Step 1: Parse document (with OCR fallback if needed)
        raw_text = await parse_document(file_path)

        # Step 2: Chunk text
        chunks = chunk_text(raw_text)
        if not chunks:
            return {"success": False, "error": "No content could be extracted from document"}

        # Step 3: Embed chunks
        vectors = embed_chunks(chunks)

        # Step 4: Ensure Qdrant collection exists and write
        client = get_qdrant_client()
        ensure_collection(client)
        write_chunks(
            client=client,
            chunks=chunks,
            vectors=vectors,
            document_id=document_id,
            user_id=DEFAULT_USER_ID,
            document_type=document_type,
            source_date=source_date,
            filename=filename,
        )

        return {
            "success": True,
            "document_id": document_id,
            "chunks_stored": len(chunks),
            "raw_text": raw_text,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
