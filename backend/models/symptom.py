import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class SymptomSeverity(str, Enum):
    mild = "mild"
    moderate = "moderate"
    severe = "severe"


class SymptomEntry(SQLModel, table=True):
    __tablename__ = "symptom_entries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: Optional[uuid.UUID] = Field(default=None, foreign_key="documents.id")
    symptom_name: str
    severity: Optional[SymptomSeverity] = None
    occurred_at: date
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
