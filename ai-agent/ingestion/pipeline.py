from langsmith import traceable

from core.logger import get_logger
from ingestion.chunker import Chunker
from ingestion.embedder import Embedder
from ingestion.parser import DocumentParser
from rag.writer import QdrantWriter

logger = get_logger(__name__)

DEFAULT_USER_ID = "default"


class IngestionPipeline:
    """
    Deterministic ingestion pipeline: parse → chunk → embed → write to Qdrant.

    This is NOT an agent — steps are fixed and sequential.
    LangSmith @traceable is used for observability only.
    """

    def __init__(
        self,
        parser: DocumentParser,
        chunker: Chunker,
        embedder: Embedder,
        writer: QdrantWriter,
    ) -> None:
        self._parser = parser
        self._chunker = chunker
        self._embedder = embedder
        self._writer = writer

    @traceable(name="ingestion_pipeline")
    async def run(
        self,
        document_id: str,
        file_path: str,
        document_type: str,
        source_date: str | None,
        filename: str,
        user_id: str = DEFAULT_USER_ID,
    ) -> dict:
        """
        Run the full ingestion pipeline for a single document.
        Returns a result dict with success status and chunk count.
        """
        logger.info(f"Ingestion start — document_id={document_id} file={file_path}")
        try:
            # Step 1: Parse
            logger.debug(f"Parsing document — {file_path}")
            raw_text = await self._parser.parse(file_path)
            logger.info(f"Parse complete — chars={len(raw_text)}")

            # Step 2: Chunk
            chunks = self._chunker.chunk(raw_text)
            logger.info(f"Chunking complete — chunks={len(chunks)}")
            if not chunks:
                logger.warning("No chunks produced — aborting ingestion")
                return {"success": False, "error": "No content could be extracted from document"}

            # Step 3: Embed
            logger.debug("Embedding chunks")
            vectors = self._embedder.embed(chunks)
            logger.info(f"Embedding complete — vectors={len(vectors)}")

            # Step 4: Write to Qdrant
            logger.debug("Writing to Qdrant")
            self._writer.write(
                chunks=chunks,
                vectors=vectors,
                document_id=document_id,
                user_id=user_id,
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
