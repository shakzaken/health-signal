from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document
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
        user_id: str | None = None,
    ) -> list[SupplementEntry]:
        stmt = (
            select(SupplementEntry)
            .join(Document, SupplementEntry.document_id == Document.id)
        )
        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)
        if from_date:
            stmt = stmt.where(SupplementEntry.started_at >= from_date)
        if to_date:
            stmt = stmt.where(
                (SupplementEntry.stopped_at >= to_date) | SupplementEntry.stopped_at.is_(None)
            )
        stmt = stmt.order_by(SupplementEntry.started_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_active(self, user_id: str | None = None) -> list[SupplementEntry]:
        """Return supplements that have not been stopped."""
        stmt = (
            select(SupplementEntry)
            .join(Document, SupplementEntry.document_id == Document.id)
            .where(SupplementEntry.stopped_at.is_(None))
            .order_by(SupplementEntry.started_at.desc())
        )
        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self, user_id: str | None = None) -> list[SupplementEntry]:
        stmt = (
            select(SupplementEntry)
            .join(Document, SupplementEntry.document_id == Document.id)
            .order_by(SupplementEntry.started_at.desc())
        )
        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
