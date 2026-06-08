import uuid
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.timeline import EventType, TimelineEvent
from repositories.timeline_repository import TimelineRepository


class TimelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = TimelineRepository(session)

    async def get_timeline(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        user_id: str | None = None,
    ) -> list[TimelineEvent]:
        return await self.repo.list_events(from_date=from_date, to_date=to_date, user_id=user_id)

    async def create_event(
        self,
        event_type: EventType,
        reference_id: uuid.UUID,
        reference_table: str,
        event_date: date,
        summary: str,
    ) -> TimelineEvent:
        event = TimelineEvent(
            event_type=event_type,
            reference_id=reference_id,
            reference_table=reference_table,
            event_date=event_date,
            summary=summary,
        )
        return await self.repo.insert_event(event)
