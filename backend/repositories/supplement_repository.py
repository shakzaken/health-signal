from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.supplement import SupplementEntry


class SupplementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, supplement: SupplementEntry) -> SupplementEntry:
        self.session.add(supplement)
        await self.session.commit()
        await self.session.refresh(supplement)
        return supplement

    async def create_entries(self, entries: list[SupplementEntry]) -> list[SupplementEntry]:
        for entry in entries:
            self.session.add(entry)
        await self.session.commit()
        return entries

    async def list_in_range(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> list[SupplementEntry]:
        query = select(SupplementEntry)
        if from_date:
            query = query.where(SupplementEntry.started_at >= from_date)
        if to_date:
            query = query.where(
                (SupplementEntry.stopped_at >= to_date) | SupplementEntry.stopped_at.is_(None)
            )
        query = query.order_by(SupplementEntry.started_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_active(self) -> list[SupplementEntry]:
        """Return supplements that have not been stopped."""
        result = await self.session.execute(
            select(SupplementEntry)
            .where(SupplementEntry.stopped_at.is_(None))
            .order_by(SupplementEntry.started_at.desc())
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[SupplementEntry]:
        result = await self.session.execute(
            select(SupplementEntry).order_by(SupplementEntry.started_at.desc())
        )
        return list(result.scalars().all())
