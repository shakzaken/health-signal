from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from repositories.supplement_repository import SupplementRepository
from schemas.supplement import SupplementEntryResponse

router = APIRouter(prefix="/supplement-entries", tags=["supplements"])


@router.get("", response_model=list[SupplementEntryResponse])
async def list_supplements(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    session: AsyncSession = Depends(get_session),
):
    repo = SupplementRepository(session)
    if from_date or to_date:
        entries = await repo.list_in_range(from_date=from_date, to_date=to_date)
    else:
        entries = await repo.list_all()
    return [
        SupplementEntryResponse(
            id=e.id,
            document_id=e.document_id,
            name=e.name,
            dosage=e.dosage,
            frequency=e.frequency,
            started_at=e.started_at,
            stopped_at=e.stopped_at,
            notes=e.notes,
            created_at=e.created_at,
        )
        for e in entries
    ]
