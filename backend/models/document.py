import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class DocumentType(str, Enum):
    blood_test = "blood_test"
    lab_report = "lab_report"
    symptom_note = "symptom_note"
    supplement_list = "supplement_list"
    diet_note = "diet_note"
    doctor_summary = "doctor_summary"
    journal = "journal"


class ProcessingStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    filename: str
    file_path: str
    document_type: DocumentType
    source_date: Optional[date] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.pending)
    raw_text: Optional[str] = None
