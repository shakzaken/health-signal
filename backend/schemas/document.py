import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from models.document import DocumentType, ProcessingStatus


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    filename: str
    document_type: DocumentType
    source_date: Optional[date]
    processing_status: ProcessingStatus
    uploaded_at: datetime


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_path: str
    document_type: DocumentType
    source_date: Optional[date]
    uploaded_at: datetime
    processing_status: ProcessingStatus
