from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.symptom import SymptomEntry


class SymptomRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, symptom: SymptomEntry) -> SymptomEntry:
        self.session.add(symptom)
        await self.session.commit()
        await self.session.refresh(symptom)
        return symptom

    async def list_by_date_range(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> list[SymptomEntry]:
        query = select(SymptomEntry)
        if from_date:
            query = query.where(SymptomEntry.occurred_at >= from_date)
        if to_date:
            query = query.where(SymptomEntry.occurred_at <= to_date)
        query = query.order_by(SymptomEntry.occurred_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())
