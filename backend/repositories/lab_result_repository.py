import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def list_all(self) -> list[LabResult]:
        result = await self.session.execute(
            select(LabResult).order_by(LabResult.test_date.desc())
        )
        return list(result.scalars().all())

    async def get_marker_history(self, marker_name: str) -> list[LabMarker]:
        """Return all historical values for a specific marker, ordered by test date."""
        result = await self.session.execute(
            select(LabMarker)
            .join(LabResult, LabMarker.lab_result_id == LabResult.id)
            .where(LabMarker.name == marker_name)
            .order_by(LabResult.test_date.asc())
        )
        return list(result.scalars().all())
