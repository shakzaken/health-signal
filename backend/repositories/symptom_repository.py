from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document
from models.symptom import SymptomEntry


class SymptomRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, symptom: SymptomEntry) -> SymptomEntry:
        self.session.add(symptom)
        await self.session.commit()
        await self.session.refresh(symptom)
        return symptom

    async def create_entries(self, entries: list[SymptomEntry]) -> list[SymptomEntry]:
        for entry in entries:
            self.session.add(entry)
        await self.session.commit()
        return entries

    async def list_all(self, user_id: str | None = None) -> list[SymptomEntry]:
        stmt = (
            select(SymptomEntry)
            .join(Document, SymptomEntry.document_id == Document.id)
            .order_by(SymptomEntry.occurred_at.desc())
        )
        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_date_range(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        user_id: str | None = None,
    ) -> list[SymptomEntry]:
        stmt = (
            select(SymptomEntry)
            .join(Document, SymptomEntry.document_id == Document.id)
        )
        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)
        if from_date:
            stmt = stmt.where(SymptomEntry.occurred_at >= from_date)
        if to_date:
            stmt = stmt.where(SymptomEntry.occurred_at <= to_date)
        stmt = stmt.order_by(SymptomEntry.occurred_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
