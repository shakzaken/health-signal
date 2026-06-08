import uuid
from typing import Optional

from datetime import date
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document
from models.lab_result import LabMarker, LabResult


class LabResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_result(self, result: LabResult) -> LabResult:
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result

    async def create_markers(self, markers: list[LabMarker]) -> list[LabMarker]:
        for marker in markers:
            self.session.add(marker)
        await self.session.commit()
        return markers

    async def get_by_id(self, result_id: uuid.UUID) -> Optional[LabResult]:
        result = await self.session.execute(
            select(LabResult).where(LabResult.id == result_id)
        )
        return result.scalar_one_or_none()

    async def get_markers_for_result(self, result_id: uuid.UUID) -> list[LabMarker]:
        result = await self.session.execute(
            select(LabMarker).where(LabMarker.lab_result_id == result_id)
        )
        return list(result.scalars().all())

    async def list_all(self, user_id: str | None = None) -> list[LabResult]:
        stmt = (
            select(LabResult)
            .join(Document, LabResult.document_id == Document.id)
            .order_by(LabResult.test_date.desc())
        )
        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_marker_history(self, marker_name: str, user_id: str | None = None) -> list[tuple[LabMarker, date]]:
        """Return all historical values for a specific marker with the test date.

        Uses case-insensitive LIKE search so 'Vitamin D' matches 'Vitamin D (25-OH)'.
        Returns list of (LabMarker, test_date) tuples ordered by test date.
        """
        pattern = f"%{marker_name}%"
        stmt = (
            select(LabMarker, LabResult.test_date)
            .join(LabResult, LabMarker.lab_result_id == LabResult.id)
            .join(Document, LabResult.document_id == Document.id)
            .where(LabMarker.name.ilike(pattern))
            .order_by(LabResult.test_date.asc())
        )
        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.all())
