import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class MarkerStatus(str, Enum):
    normal = "normal"
    low = "low"
    high = "high"
    borderline_low = "borderline_low"
    borderline_high = "borderline_high"


class LabResult(SQLModel, table=True):
    __tablename__ = "lab_results"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(foreign_key="documents.id")
    test_date: date
    lab_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LabMarker(SQLModel, table=True):
    __tablename__ = "lab_markers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    lab_result_id: uuid.UUID = Field(foreign_key="lab_results.id")
    name: str
    value: float
    unit: str
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    status: Optional[MarkerStatus] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
