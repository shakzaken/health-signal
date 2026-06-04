import uuid
from enum import Enum

from datetime import date, datetime, timezone
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class EventType(str, Enum):
    lab_result = "lab_result"
    symptom = "symptom"
    supplement_change = "supplement_change"
    diet_change = "diet_change"
    note = "note"


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_type: Mapped[EventType] = mapped_column(SAEnum(EventType, native_enum=False))
    reference_id: Mapped[uuid.UUID]
    reference_table: Mapped[str]
    event_date: Mapped[date]
    summary: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
