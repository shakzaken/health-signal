from datetime import date
from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document
from models.lab_result import LabResult
from models.supplement import SupplementEntry
from models.symptom import SymptomEntry
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
        user_id: str | None = None,
    ) -> list[TimelineEvent]:
        stmt = select(TimelineEvent)
        if user_id is not None:
            # Filter by user via subqueries through each reference table's document FK
            lab_ids = (
                select(LabResult.id)
                .join(Document, LabResult.document_id == Document.id)
                .where(Document.user_id == user_id)
                .scalar_subquery()
            )
            symptom_ids = (
                select(SymptomEntry.id)
                .join(Document, SymptomEntry.document_id == Document.id)
                .where(Document.user_id == user_id)
                .scalar_subquery()
            )
            supplement_ids = (
                select(SupplementEntry.id)
                .join(Document, SupplementEntry.document_id == Document.id)
                .where(Document.user_id == user_id)
                .scalar_subquery()
            )
            stmt = stmt.where(
                or_(
                    and_(TimelineEvent.reference_table == "lab_results", TimelineEvent.reference_id.in_(lab_ids)),
                    and_(TimelineEvent.reference_table == "symptom_entries", TimelineEvent.reference_id.in_(symptom_ids)),
                    and_(TimelineEvent.reference_table == "supplement_entries", TimelineEvent.reference_id.in_(supplement_ids)),
                )
            )
        if from_date:
            stmt = stmt.where(TimelineEvent.event_date >= from_date)
        if to_date:
            stmt = stmt.where(TimelineEvent.event_date <= to_date)
        stmt = stmt.order_by(TimelineEvent.event_date.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
