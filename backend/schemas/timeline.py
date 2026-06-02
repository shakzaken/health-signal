import uuid
from datetime import date, datetime

from pydantic import BaseModel

from models.timeline import EventType


class TimelineEventResponse(BaseModel):
    id: uuid.UUID
    event_type: EventType
    reference_id: uuid.UUID
    reference_table: str
    event_date: date
    summary: str
    created_at: datetime
