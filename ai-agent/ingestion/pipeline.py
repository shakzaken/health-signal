import asyncio

from langchain_core.runnables.config import RunnableConfig
from langchain_core.tracers.langchain import LangChainTracer

from core.logger import get_logger
from ingestion.chunker import Chunker
from ingestion.embedder import Embedder
from ingestion.parser import DocumentParser
from rag.writer import QdrantWriter
from tools.document_classifier import DocumentClassifier
from tools.lab_extractor import LabExtractor
from tools.supplement_extractor import SupplementExtractor
from tools.symptom_extractor import SymptomExtractor

logger = get_logger(__name__)

DEFAULT_USER_ID = "default"

LAB_DOCUMENT_TYPES = frozenset({"blood_test", "lab_report"})
SYMPTOM_DOCUMENT_TYPES = frozenset({"symptom_note", "journal"})
SUPPLEMENT_DOCUMENT_TYPES = frozenset({"supplement_list"})


class IngestionPipeline:
    """
    Ingestion pipeline: parse → classify? → chunk → embed → write to Qdrant → extract.

    Parallel execution:
      - Classification and chunking run concurrently (both only need raw_text).
      - Embedding and structured extraction run concurrently (extraction is an LLM call,
        embedding is CPU-bound — asyncio.to_thread keeps the event loop unblocked).

    LangSmith trace:
      All LLM calls (parser vision OCR, classifier, extractors) receive the same config,
      so they appear nested under a single ingestion trace automatically.
    """

    def __init__(
        self,
        parser: DocumentParser,
        chunker: Chunker,
        embedder: Embedder,
        writer: QdrantWriter,
        lab_extractor: LabExtractor,
        symptom_extractor: SymptomExtractor,
        supplement_extractor: SupplementExtractor,
        classifier: DocumentClassifier,
    ) -> None:
        self._parser = parser
        self._chunker = chunker
        self._embedder = embedder
        self._writer = writer
        self._classifier = classifier
        # dispatch table: frozenset of doc types → (result key, extractor instance)
        self._extractors = {
            LAB_DOCUMENT_TYPES: ("lab_result", lab_extractor),
            SYMPTOM_DOCUMENT_TYPES: ("symptom_data", symptom_extractor),
            SUPPLEMENT_DOCUMENT_TYPES: ("supplement_data", supplement_extractor),
        }

    async def run(
        self,
        document_id: str,
        file_path: str,
        document_type: str | None,
        source_date: str | None,
        filename: str,
        user_id: str | None = None,
    ) -> dict:
        if not user_id:
            logger.warning(
                f"No user_id supplied for document_id={document_id} — "
                f"falling back to DEFAULT_USER_ID='{DEFAULT_USER_ID}'. "
                "This document will not be retrievable by any real user."
            )
        user_id = user_id or DEFAULT_USER_ID
        logger.info(f"Ingestion start — document_id={document_id} file={file_path}")
        config: RunnableConfig = {
            "callbacks": [LangChainTracer()],
            "run_name": f"ingestion/{filename}",
            "metadata": {
                "user_id": user_id,
                "document_id": document_id,
                "filename": filename,
                "document_type": document_type or "auto",
            },
            "tags": ["ingestion", document_type or "auto"],
        }

        try:
            # Step 1: Parse (vision OCR fallback for image-based PDFs)
            raw_text = await self._parser.parse(file_path, config=config)
            logger.info(f"Parse complete — chars={len(raw_text)}")

            if not raw_text.strip():
                return {"success": False, "error": "No content could be extracted from document"}

            # Step 2: Classify (if needed) + Chunk — run in parallel
            detected_document_type: str | None = None
            if document_type is None:
                document_type, chunks = await asyncio.gather(
                    self._classifier.classify(raw_text, config=config),
                    asyncio.to_thread(self._chunker.chunk, raw_text),
                )
                detected_document_type = document_type
                logger.info(f"Classification complete — document_type={document_type}")
            else:
                chunks = await asyncio.to_thread(self._chunker.chunk, raw_text)

            logger.info(f"Chunking complete — chunks={len(chunks)}")
            if not chunks:
                return {"success": False, "error": "No content could be extracted from document"}

            # Step 3: Embed (CPU) + Extract (LLM) — run in parallel
            vectors, extracted = await asyncio.gather(
                self._embedder.embed(chunks),
                self._extract(raw_text, document_type, config),
            )
            logger.info(f"Embedding complete — vectors={len(vectors)}")

            # Step 4: Write to Qdrant
            self._writer.write(
                chunks=chunks,
                vectors=vectors,
                document_id=document_id,
                user_id=user_id,
                document_type=document_type,
                source_date=source_date,
                filename=filename,
            )
            logger.info(f"Qdrant write complete — document_id={document_id} chunks={len(chunks)}")
            logger.info(f"Ingestion complete — document_id={document_id}")

            return {
                "success": True,
                "document_id": document_id,
                "chunks_stored": len(chunks),
                "detected_document_type": detected_document_type,
                **extracted,
            }

        except Exception as e:
            logger.exception(f"Ingestion failed — document_id={document_id} error={e}")
            return {"success": False, "error": str(e)}

    async def _extract(
        self,
        raw_text: str,
        document_type: str,
        config: RunnableConfig,
    ) -> dict:
        """Run the appropriate structured extractor for the document type."""
        for doc_types, (key, extractor) in self._extractors.items():
            if document_type not in doc_types:
                continue
            result = await extractor.extract(raw_text, config=config)
            data = getattr(result, "markers", None) or getattr(result, "entries", None)
            if data:
                logger.info(f"Extraction complete — type={document_type} count={len(data)}")
            else:
                logger.warning(f"No data extracted — type={document_type}")
            return {key: result.model_dump()} if data else {}
        return {}
