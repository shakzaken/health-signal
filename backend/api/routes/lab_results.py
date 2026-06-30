import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from db.session import get_session
from models.user import User
from repositories.lab_result_repository import LabResultRepository
from schemas.lab_result import LabMarkerResponse, LabResultResponse, MarkerHistoryResponse

router = APIRouter(prefix="/api/lab-results", tags=["lab-results"])


@router.get("", response_model=list[LabResultResponse])
async def list_lab_results(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    repo = LabResultRepository(session)
    results = await repo.list_all(user_id=str(current_user.id))
    output = []
    for r in results:
        markers = await repo.get_markers_for_result(r.id)
        output.append(
            LabResultResponse(
                id=r.id,
                document_id=r.document_id,
                test_date=r.test_date,
                lab_name=r.lab_name,
                created_at=r.created_at,
                markers=[
                    LabMarkerResponse(
                        id=m.id,
                        lab_result_id=m.lab_result_id,
                        name=m.name,
                        value=m.value,
                        unit=m.unit,
                        reference_low=m.reference_low,
                        reference_high=m.reference_high,
                        status=m.status,
                        created_at=m.created_at,
                    )
                    for m in markers
                ],
            )
        )
    return output


@router.get("/markers/{marker_name}/history", response_model=MarkerHistoryResponse)
async def get_marker_history(
    marker_name: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    repo = LabResultRepository(session)
    rows = await repo.get_marker_history(marker_name, user_id=str(current_user.id))
    return MarkerHistoryResponse(
        name=marker_name,
        history=[
            LabMarkerResponse(
                id=m.id,
                lab_result_id=m.lab_result_id,
                name=m.name,
                value=m.value,
                unit=m.unit,
                reference_low=m.reference_low,
                reference_high=m.reference_high,
                status=m.status,
                created_at=m.created_at,
                test_date=test_date,
            )
            for m, test_date in rows
        ],
    )


@router.get("/{result_id}", response_model=LabResultResponse)
async def get_lab_result(
    result_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    repo = LabResultRepository(session)
    result = await repo.get_by_id(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Lab result not found")
    markers = await repo.get_markers_for_result(result_id)
    return LabResultResponse(
        id=result.id,
        document_id=result.document_id,
        test_date=result.test_date,
        lab_name=result.lab_name,
        created_at=result.created_at,
        markers=[
            LabMarkerResponse(
                id=m.id,
                lab_result_id=m.lab_result_id,
                name=m.name,
                value=m.value,
                unit=m.unit,
                reference_low=m.reference_low,
                reference_high=m.reference_high,
                status=m.status,
                created_at=m.created_at,
            )
            for m in markers
        ],
    )
