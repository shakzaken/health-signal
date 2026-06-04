import uuid
from enum import Enum
from typing import Optional

from datetime import date, datetime, timezone
from sqlalchemy import Enum as SAEnum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class SymptomSeverity(str, Enum):
    mild = "mild"
    moderate = "moderate"
    severe = "severe"


class SymptomEntry(Base):
    __tablename__ = "symptom_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("documents.id"), nullable=True, default=None
    )
    symptom_name: Mapped[str]
    severity: Mapped[Optional[SymptomSeverity]] = mapped_column(
        SAEnum(SymptomSeverity, native_enum=False), nullable=True, default=None
    )
    occurred_at: Mapped[date]
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
