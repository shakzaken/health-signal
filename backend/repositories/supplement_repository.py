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
