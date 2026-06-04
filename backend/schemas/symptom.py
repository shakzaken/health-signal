import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from models.symptom import SymptomSeverity


class SymptomEntryCreate(BaseModel):
    document_id: Optional[uuid.UUID] = None
    symptom_name: str
    severity: Optional[SymptomSeverity] = None
    occurred_at: date
    notes: Optional[str] = None


class SymptomEntryResponse(BaseModel):
    id: uuid.UUID
    document_id: Optional[uuid.UUID]
    symptom_name: str
    severity: Optional[SymptomSeverity]
    occurred_at: date
    notes: Optional[str]
    created_at: datetime
