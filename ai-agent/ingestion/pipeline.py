from langchain_core.callbacks.manager import atrace_as_chain_group
from langchain_core.runnables.config import RunnableConfig

from core.logger import get_logger
from ingestion.chunker import Chunker
from ingestion.embedder import Embedder
from ingestion.parser import DocumentParser
from rag.writer import QdrantWriter
from tools.document_classifier import DocumentClassifier
from tools.lab_extractor import ExtractedLabResult, LabExtractor
from tools.supplement_extractor import ExtractedSupplements, SupplementExtractor
from tools.symptom_extractor import ExtractedSymptoms, SymptomExtractor

logger = get_logger(__name__)

DEFAULT_USER_ID = "default"

LAB_DOCUMENT_TYPES = {"blood_test", "lab_report"}
SYMPTOM_DOCUMENT_TYPES = {"symptom_note", "journal"}
SUPPLEMENT_DOCUMENT_TYPES = {"supplement_list"}


class IngestionPipeline:
    """
    Ingestion pipeline: parse → chunk → embed → write to Qdrant.
    For structured document types, also extracts data via LLM:
      - blood_test / lab_report   → LabExtractor    → lab_result in response
      - symptom_note / journal    → SymptomExtractor → symptom_data in response
      - supplement_list           → SupplementExtractor → supplement_data in response

    The backend is responsible for persisting the extracted data to PostgreSQL.

    LangSmith trace hierarchy:
        ingestion_pipeline
          ├── document_parsing
          │   └── ChatOpenAI  (vision OCR — only for scanned PDFs)
          ├── document_classification  (only when document_type not provided)
          ├── lab_extraction       (only for lab document types)
          ├── symptom_extraction   (only for symptom document types)
          └── supplement_extraction (only for supplement document types)
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
        self._lab_extractor = lab_extractor
        self._symptom_extractor = symptom_extractor
        self._supplement_extractor = supplement_extractor
        self._classifier = classifier

    async def run(
        self,
        document_id: str,
        file_path: str,
        document_type: str | None,
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
        5. Extract structured data based on document_type

        Returns a result dict with success status, chunk count, and optional
        lab_result / symptom_data / supplement_data depending on document type.
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
        document_type: str | None,
        source_date: str | None,
        filename: str,
        user_id: str,
        pipeline_manager,
    ) -> dict:
        # Step 1: Parse
        logger.debug(f"Parsing document — {file_path}")
        async with atrace_as_chain_group(
            "document_parsing",
            callback_manager=pipeline_manager,
            inputs={"file_path": file_path},
        ) as parse_manager:
            parse_config: RunnableConfig = {"callbacks": parse_manager}
            raw_text = await self._parser.parse(file_path, config=parse_config)
        logger.info(f"Parse complete — chars={len(raw_text)}")

        # Step 1b: Classify document type if not provided
        detected_type: str | None = None
        if document_type is None:
            logger.info(f"No document type provided — classifying — document_id={document_id}")
            async with atrace_as_chain_group(
                "document_classification",
                callback_manager=pipeline_manager,
                inputs={"chars": len(raw_text)},
            ) as classify_manager:
                document_type = await self._classifier.classify(
                    raw_text, config={"callbacks": classify_manager}
                )
            detected_type = document_type
            logger.info(f"Classification complete — document_type={document_type}")

        # Step 2: Chunk
        chunks = self._chunker.chunk(raw_text)
        logger.info(f"Chunking complete — chunks={len(chunks)}")
        if not chunks:
            logger.warning("No chunks produced — aborting ingestion")
            return {"success": False, "error": "No content could be extracted from document"}

        # Step 3: Embed
        vectors = self._embedder.embed(chunks)
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
        logger.info(f"Qdrant write complete — document_id={document_id} chunks_stored={len(chunks)}")

        result: dict = {
            "success": True,
            "document_id": document_id,
            "chunks_stored": len(chunks),
            "raw_text": raw_text,
            "detected_document_type": detected_type,
        }

        # Step 5: Structured extraction based on document type
        if document_type in LAB_DOCUMENT_TYPES:
            logger.info(f"Extracting lab markers — document_id={document_id}")
            async with atrace_as_chain_group(
                "lab_extraction",
                callback_manager=pipeline_manager,
                inputs={"document_type": document_type},
            ) as extract_manager:
                lab_result: ExtractedLabResult = await self._lab_extractor.extract(
                    raw_text, config={"callbacks": extract_manager}
                )
            if lab_result.markers:
                logger.info(f"Lab extraction complete — markers={len(lab_result.markers)}")
                result["lab_result"] = lab_result.model_dump()
            else:
                logger.warning("No markers extracted from lab document")

        elif document_type in SYMPTOM_DOCUMENT_TYPES:
            logger.info(f"Extracting symptoms — document_id={document_id}")
            async with atrace_as_chain_group(
                "symptom_extraction",
                callback_manager=pipeline_manager,
                inputs={"document_type": document_type},
            ) as extract_manager:
                symptom_result: ExtractedSymptoms = await self._symptom_extractor.extract(
                    raw_text, config={"callbacks": extract_manager}
                )
            if symptom_result.entries:
                logger.info(f"Symptom extraction complete — entries={len(symptom_result.entries)}")
                result["symptom_data"] = symptom_result.model_dump()
            else:
                logger.warning("No symptoms extracted from document")

        elif document_type in SUPPLEMENT_DOCUMENT_TYPES:
            logger.info(f"Extracting supplements — document_id={document_id}")
            async with atrace_as_chain_group(
                "supplement_extraction",
                callback_manager=pipeline_manager,
                inputs={"document_type": document_type},
            ) as extract_manager:
                supplement_result: ExtractedSupplements = await self._supplement_extractor.extract(
                    raw_text, config={"callbacks": extract_manager}
                )
            if supplement_result.entries:
                logger.info(f"Supplement extraction complete — entries={len(supplement_result.entries)}")
                result["supplement_data"] = supplement_result.model_dump()
            else:
                logger.warning("No supplements extracted from document")

        logger.info(f"Ingestion complete — document_id={document_id}")
        return result
