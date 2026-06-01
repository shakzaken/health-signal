import uuid
from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class SupplementEntry(SQLModel, table=True):
    __tablename__ = "supplement_entries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: Optional[uuid.UUID] = Field(default=None, foreign_key="documents.id")
    name: str
    dosage: str
    frequency: str
    started_at: Optional[date] = None
    stopped_at: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
