import uuid
from datetime import date, datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class EventType(str, Enum):
    lab_result = "lab_result"
    symptom = "symptom"
    supplement_change = "supplement_change"
    diet_change = "diet_change"
    note = "note"


class TimelineEvent(SQLModel, table=True):
    __tablename__ = "timeline_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    event_type: EventType
    reference_id: uuid.UUID
    reference_table: str
    event_date: date
    summary: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
