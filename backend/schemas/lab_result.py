import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from models.lab_result import MarkerStatus


# ── Request schemas (used when saving extracted lab data) ────────────────────

class LabMarkerCreate(BaseModel):
    name: str
    value: float
    unit: str
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    status: Optional[str] = None


class LabResultCreate(BaseModel):
    document_id: uuid.UUID
    test_date: date
    lab_name: Optional[str] = None
    markers: list[LabMarkerCreate] = []


# ── Response schemas ─────────────────────────────────────────────────────────

class LabMarkerResponse(BaseModel):
    id: uuid.UUID
    lab_result_id: uuid.UUID
    name: str
    value: float
    unit: str
    reference_low: Optional[float]
    reference_high: Optional[float]
    status: Optional[MarkerStatus]
    created_at: datetime


class LabResultResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    test_date: date
    lab_name: Optional[str]
    created_at: datetime
    markers: list[LabMarkerResponse] = []


class MarkerHistoryResponse(BaseModel):
    name: str
    history: list[LabMarkerResponse]
