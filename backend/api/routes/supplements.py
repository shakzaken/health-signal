from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from db.session import get_session
from models.user import User
from repositories.supplement_repository import SupplementRepository
from schemas.supplement import SupplementEntryResponse

router = APIRouter(prefix="/api/supplement-entries", tags=["supplements"])


@router.get("", response_model=list[SupplementEntryResponse])
async def list_supplements(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    repo = SupplementRepository(session)
    user_id = str(current_user.id)
    if from_date or to_date:
        entries = await repo.list_in_range(from_date=from_date, to_date=to_date, user_id=user_id)
    else:
        entries = await repo.list_all(user_id=user_id)
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
