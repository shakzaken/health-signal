import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class SupplementEntryCreate(BaseModel):
    document_id: Optional[uuid.UUID] = None
    name: str
    dosage: str
    frequency: str
    started_at: Optional[date] = None
    stopped_at: Optional[date] = None
    notes: Optional[str] = None


class SupplementEntryResponse(BaseModel):
    id: uuid.UUID
    document_id: Optional[uuid.UUID]
    name: str
    dosage: str
    frequency: str
    started_at: Optional[date]
    stopped_at: Optional[date]
    notes: Optional[str]
    created_at: datetime
