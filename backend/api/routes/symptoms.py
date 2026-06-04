from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from repositories.symptom_repository import SymptomRepository
from schemas.symptom import SymptomEntryResponse

router = APIRouter(prefix="/symptom-entries", tags=["symptoms"])


@router.get("", response_model=list[SymptomEntryResponse])
async def list_symptoms(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    session: AsyncSession = Depends(get_session),
):
    repo = SymptomRepository(session)
    if from_date or to_date:
        entries = await repo.list_by_date_range(from_date=from_date, to_date=to_date)
    else:
        entries = await repo.list_all()
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
