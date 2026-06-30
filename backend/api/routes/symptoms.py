from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from db.session import get_session
from models.user import User
from repositories.symptom_repository import SymptomRepository
from schemas.symptom import SymptomEntryResponse

router = APIRouter(prefix="/api/symptom-entries", tags=["symptoms"])


@router.get("", response_model=list[SymptomEntryResponse])
async def list_symptoms(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    repo = SymptomRepository(session)
    user_id = str(current_user.id)
    if from_date or to_date:
        entries = await repo.list_by_date_range(from_date=from_date, to_date=to_date, user_id=user_id)
    else:
        entries = await repo.list_all(user_id=user_id)
    return [
        SymptomEntryResponse(
            id=e.id,
            document_id=e.document_id,
            symptom_name=e.symptom_name,
            severity=e.severity,
            occurred_at=e.occurred_at,
            notes=e.notes,
            created_at=e.created_at,
        )
        for e in entries
    ]
