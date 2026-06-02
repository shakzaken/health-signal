from langsmith import traceable

from core.logger import get_logger
from ingestion.chunker import Chunker
from ingestion.embedder import Embedder
from ingestion.parser import DocumentParser
from rag.writer import QdrantWriter
from tools.lab_extractor import ExtractedLabResult, LabExtractor

logger = get_logger(__name__)

DEFAULT_USER_ID = "default"

# Document types that contain structured lab data worth extracting
LAB_DOCUMENT_TYPES = {"blood_test", "lab_report"}


class IngestionPipeline:
    """
    Ingestion pipeline: parse → chunk → embed → write to Qdrant.
    For lab documents, also extracts structured markers via LLM and returns them
    so the backend can persist them to PostgreSQL.

    This is NOT an agent — steps are fixed and sequential.
    LangSmith @traceable is used for observability only.
    """

    def __init__(
        self,
        parser: DocumentParser,
        chunker: Chunker,
        embedder: Embedder,
        writer: QdrantWriter,
        lab_extractor: LabExtractor,
    ) -> None:
        self._parser = parser
        self._chunker = chunker
        self._embedder = embedder
        self._writer = writer
        self._lab_extractor = lab_extractor

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

        Steps:
        1. Parse raw text (PDF/text/vision OCR)
        2. Chunk text
        3. Embed chunks
        4. Write to Qdrant
        5. If lab document: extract structured markers and return them

        Returns a result dict with success status, chunk count, and optional lab_result.
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
            logger.info(f"Qdrant write complete — document_id={document_id} chunks_stored={len(chunks)}")

            result: dict = {
                "success": True,
                "document_id": document_id,
                "chunks_stored": len(chunks),
                "raw_text": raw_text,
            }

            # Step 5: Extract structured lab markers for lab documents
            if document_type in LAB_DOCUMENT_TYPES:
                logger.info(f"Extracting structured lab markers — document_id={document_id}")
                lab_result: ExtractedLabResult = await self._lab_extractor.extract(raw_text)
                if lab_result.markers:
                    logger.info(f"Extraction complete — markers={len(lab_result.markers)}")
                    result["lab_result"] = lab_result.model_dump()
                else:
                    logger.warning("No markers extracted from lab document")

            logger.info(f"Ingestion complete — document_id={document_id}")
            return result

        except Exception as e:
            logger.exception(f"Ingestion failed — document_id={document_id} error={e}")
            return {"success": False, "error": str(e)}
