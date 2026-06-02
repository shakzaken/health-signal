from datetime import date
from typing import Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from models.timeline import TimelineEvent
from repositories.timeline_repository import TimelineRepository


class TimelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = TimelineRepository(session)

    async def get_timeline(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> list[TimelineEvent]:
        return await self.repo.list_events(from_date=from_date, to_date=to_date)
