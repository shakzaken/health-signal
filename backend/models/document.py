import uuid
from enum import Enum
from typing import Optional

from datetime import UTC, date, datetime
from sqlalchemy import Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


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


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filename: Mapped[str]
    file_path: Mapped[str]
    document_type: Mapped[DocumentType] = mapped_column(SAEnum(DocumentType, native_enum=False))
    source_date: Mapped[Optional[date]] = mapped_column(nullable=True, default=None)
    uploaded_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC).replace(tzinfo=None))
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        SAEnum(ProcessingStatus, native_enum=False),
        default=ProcessingStatus.pending,
    )
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
