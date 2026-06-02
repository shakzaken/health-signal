from langsmith import traceable

from core.logger import get_logger
from ingestion.chunker import chunk_text
from ingestion.embedder import embed_chunks
from ingestion.parser import parse_document
from rag.qdrant_client import ensure_collection, get_qdrant_client
from rag.writer import write_chunks

logger = get_logger(__name__)

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
    logger.info(f"Ingestion start — document_id={document_id} file={file_path}")
    try:
        # Step 1: Parse
        logger.debug(f"Parsing document — {file_path}")
        raw_text = await parse_document(file_path)
        logger.info(f"Parse complete — chars={len(raw_text)}")

        # Step 2: Chunk
        chunks = chunk_text(raw_text)
        logger.info(f"Chunking complete — chunks={len(chunks)}")
        if not chunks:
            logger.warning("No chunks produced — aborting ingestion")
            return {"success": False, "error": "No content could be extracted from document"}

        # Step 3: Embed
        logger.debug("Embedding chunks")
        vectors = embed_chunks(chunks)
        logger.info(f"Embedding complete — vectors={len(vectors)}")

        # Step 4: Write to Qdrant
        logger.debug("Writing to Qdrant")
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
        logger.info(f"Ingestion complete — document_id={document_id} chunks_stored={len(chunks)}")

        return {
            "success": True,
            "document_id": document_id,
            "chunks_stored": len(chunks),
            "raw_text": raw_text,
        }

    except Exception as e:
        logger.exception(f"Ingestion failed — document_id={document_id} error={e}")
        return {"success": False, "error": str(e)}
