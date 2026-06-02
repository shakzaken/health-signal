from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.timeline import TimelineEvent


class TimelineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert_event(self, event: TimelineEvent) -> TimelineEvent:
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def list_events(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> list[TimelineEvent]:
        query = select(TimelineEvent)
        if from_date:
            query = query.where(TimelineEvent.event_date >= from_date)
        if to_date:
            query = query.where(TimelineEvent.event_date <= to_date)
        query = query.order_by(TimelineEvent.event_date.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())
