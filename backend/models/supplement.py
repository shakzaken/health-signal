import uuid
from typing import Optional

from datetime import date, datetime, timezone
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class SupplementEntry(Base):
    __tablename__ = "supplement_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("documents.id"), nullable=True, default=None
    )
    name: Mapped[str]
    dosage: Mapped[str]
    frequency: Mapped[str]
    started_at: Mapped[Optional[date]] = mapped_column(nullable=True, default=None)
    stopped_at: Mapped[Optional[date]] = mapped_column(nullable=True, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
