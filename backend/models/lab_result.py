import uuid
from enum import Enum
from typing import Optional

from datetime import date, datetime, timezone
from sqlalchemy import Enum as SAEnum, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class MarkerStatus(str, Enum):
    normal = "normal"
    low = "low"
    high = "high"
    borderline_low = "borderline_low"
    borderline_high = "borderline_high"


class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"))
    test_date: Mapped[date]
    lab_name: Mapped[Optional[str]] = mapped_column(nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class LabMarker(Base):
    __tablename__ = "lab_markers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lab_result_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lab_results.id"))
    name: Mapped[str]
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str]
    reference_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    reference_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    status: Mapped[Optional[MarkerStatus]] = mapped_column(
        SAEnum(MarkerStatus, native_enum=False), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
