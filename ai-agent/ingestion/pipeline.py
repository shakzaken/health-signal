from langchain_core.callbacks.manager import atrace_as_chain_group
from langchain_core.runnables.config import RunnableConfig

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

    Each meaningful step gets its own named span via atrace_as_chain_group so
    LangSmith shows a clear hierarchy:

        ingestion_pipeline
          ├── document_parsing
          │   └── ChatOpenAI  (vision OCR — only when PDF needs it)
          └── lab_extraction
              └── ChatOpenAI  (structured output — only for lab documents)
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

        async with atrace_as_chain_group(
            "ingestion_pipeline",
            inputs={"document_id": document_id, "file_path": file_path, "document_type": document_type},
        ) as pipeline_manager:
            try:
                return await self._run_steps(
                    document_id=document_id,
                    file_path=file_path,
                    document_type=document_type,
                    source_date=source_date,
                    filename=filename,
                    user_id=user_id,
                    pipeline_manager=pipeline_manager,
                )
            except Exception as e:
                logger.exception(f"Ingestion failed — document_id={document_id} error={e}")
                return {"success": False, "error": str(e)}

    async def _run_steps(
        self,
        document_id: str,
        file_path: str,
        document_type: str,
        source_date: str | None,
        filename: str,
        user_id: str,
        pipeline_manager,
    ) -> dict:
        # Step 1: Parse — named span so vision OCR appears under "document_parsing"
        logger.debug(f"Parsing document — {file_path}")
        async with atrace_as_chain_group(
            "document_parsing",
            callback_manager=pipeline_manager,
            inputs={"file_path": file_path},
        ) as parse_manager:
            parse_config: RunnableConfig = {"callbacks": parse_manager}
            raw_text = await self._parser.parse(file_path, config=parse_config)
        logger.info(f"Parse complete — chars={len(raw_text)}")

        # Step 2: Chunk (CPU-only, not traced)
        chunks = self._chunker.chunk(raw_text)
        logger.info(f"Chunking complete — chunks={len(chunks)}")
        if not chunks:
            logger.warning("No chunks produced — aborting ingestion")
            return {"success": False, "error": "No content could be extracted from document"}

        # Step 3: Embed (CPU/local model, not traced)
        logger.debug("Embedding chunks")
        vectors = self._embedder.embed(chunks)
        logger.info(f"Embedding complete — vectors={len(vectors)}")

        # Step 4: Write to Qdrant (not traced)
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

        # Step 5: Extract structured lab markers — named span so the LLM call
        # appears under "lab_extraction" rather than floating at pipeline level
        if document_type in LAB_DOCUMENT_TYPES:
            logger.info(f"Extracting structured lab markers — document_id={document_id}")
            async with atrace_as_chain_group(
                "lab_extraction",
                callback_manager=pipeline_manager,
                inputs={"document_type": document_type},
            ) as extract_manager:
                extract_config: RunnableConfig = {"callbacks": extract_manager}
                lab_result: ExtractedLabResult = await self._lab_extractor.extract(
                    raw_text, config=extract_config
                )
            if lab_result.markers:
                logger.info(f"Extraction complete — markers={len(lab_result.markers)}")
                result["lab_result"] = lab_result.model_dump()
            else:
                logger.warning("No markers extracted from lab document")

        logger.info(f"Ingestion complete — document_id={document_id}")
        return result
