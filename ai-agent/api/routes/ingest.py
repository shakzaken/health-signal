from datetime import date
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ingestion.pipeline import run_ingestion

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    document_id: str
    file_path: str
    document_type: str
    source_date: Optional[str] = None
    filename: str = ""


class IngestResponse(BaseModel):
    success: bool
    document_id: str
    chunks_stored: int = 0
    error: Optional[str] = None


@router.post("", response_model=IngestResponse)
async def ingest_document(request: IngestRequest):
    result = await run_ingestion(
        document_id=request.document_id,
        file_path=request.file_path,
        document_type=request.document_type,
        source_date=request.source_date,
        filename=request.filename or request.file_path.split("/")[-1],
    )
    return IngestResponse(
        success=result["success"],
        document_id=request.document_id,
        chunks_stored=result.get("chunks_stored", 0),
        error=result.get("error"),
    )
