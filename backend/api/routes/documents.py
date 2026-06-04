import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from models.document import DocumentType
from repositories.document_repository import DocumentRepository
from schemas.document import DocumentResponse, DocumentUploadResponse
from services.document_service import DocumentService

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[DocumentType] = Form(None),
    source_date: Optional[date] = Form(None),
    session: AsyncSession = Depends(get_session),
):
    logger.info(f"Upload request — filename={file.filename} type={document_type} date={source_date}")
    try:
        service = DocumentService(session)
        document = await service.upload(file, document_type, source_date)
        logger.info(f"Upload success — document_id={document.id} status={document.processing_status}")
        return DocumentUploadResponse(
            id=document.id,
            filename=document.filename,
            document_type=document.document_type,
            source_date=document.source_date,
            processing_status=document.processing_status,
            uploaded_at=document.uploaded_at,
        )
    except Exception as e:
        logger.exception(f"Upload failed — {e}")
        raise


@router.get("", response_model=list[DocumentResponse])
async def list_documents(session: AsyncSession = Depends(get_session)):
    logger.debug("List documents request")
    repo = DocumentRepository(session)
    documents = await repo.list_all()
    logger.debug(f"Found {len(documents)} documents")
    return [
        DocumentResponse(
            id=d.id,
            filename=d.filename,
            file_path=d.file_path,
            document_type=d.document_type,
            source_date=d.source_date,
            uploaded_at=d.uploaded_at,
            processing_status=d.processing_status,
        )
        for d in documents
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    logger.debug(f"Get document request — document_id={document_id}")
    repo = DocumentRepository(session)
    document = await repo.get_by_id(document_id)
    if not document:
        logger.warning(f"Document not found — document_id={document_id}")
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_path=document.file_path,
        document_type=document.document_type,
        source_date=document.source_date,
        uploaded_at=document.uploaded_at,
        processing_status=document.processing_status,
    )
