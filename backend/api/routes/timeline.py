from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from schemas.timeline import TimelineEventResponse
from services.timeline_service import TimelineService

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("", response_model=list[TimelineEventResponse])
async def get_timeline(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    session: AsyncSession = Depends(get_session),
):
    service = TimelineService(session)
    events = await service.get_timeline(from_date=from_date, to_date=to_date)
    return [
        TimelineEventResponse(
            id=e.id,
            event_type=e.event_type,
            reference_id=e.reference_id,
            reference_table=e.reference_table,
            event_date=e.event_date,
            summary=e.summary,
            created_at=e.created_at,
        )
        for e in events
    ]
