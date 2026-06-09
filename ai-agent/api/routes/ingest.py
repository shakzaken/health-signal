from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import get_ingestion_pipeline
from core.logger import get_logger
from ingestion.pipeline import IngestionPipeline

logger = get_logger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    document_id: str
    file_path: str
    document_type: Optional[str] = None
    source_date: Optional[str] = None
    filename: str = ""
    user_id: Optional[str] = None


class IngestResponse(BaseModel):
    success: bool
    document_id: str
    chunks_stored: int = 0
    error: Optional[str] = None
    lab_result: Optional[dict[str, Any]] = None
    symptom_data: Optional[dict[str, Any]] = None
    supplement_data: Optional[dict[str, Any]] = None
    detected_document_type: Optional[str] = None


@router.post("", response_model=IngestResponse)
async def ingest_document(
    request: IngestRequest,
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
):
    logger.info(f"Ingest request — document_id={request.document_id} file={request.file_path}")
    result = await pipeline.run(
        document_id=request.document_id,
        file_path=request.file_path,
        document_type=request.document_type,
        source_date=request.source_date,
        filename=request.filename or request.file_path.split("/")[-1],
        user_id=request.user_id,
    )
    if not result["success"]:
        logger.error(f"Ingest failed — document_id={request.document_id} error={result.get('error')}")
    return IngestResponse(
        success=result["success"],
        document_id=request.document_id,
        chunks_stored=result.get("chunks_stored", 0),
        error=result.get("error"),
        lab_result=result.get("lab_result"),
        symptom_data=result.get("symptom_data"),
        supplement_data=result.get("supplement_data"),
        detected_document_type=result.get("detected_document_type"),
    )
