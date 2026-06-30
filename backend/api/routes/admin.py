import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin_user
from core.logger import get_logger
from core.security import hash_password
from db.session import get_session
from models.usage_event import UsageEventType
from models.user import User
from repositories.user_repository import UserRepository
from repositories.usage_event_repository import UsageEventRepository, days_ago
from schemas.admin import AdminCreateUserRequest, AdminDeleteUserRequest, AdminStatsResponse, AdminUserResponse
from services.user_deletion_service import UserDeletionService

logger = get_logger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(get_current_admin_user),
):
    user_repo = UserRepository(session)
    usage_repo = UsageEventRepository(session)

    return AdminStatsResponse(
        total_users=await user_repo.count_all(),
        total_queries=await usage_repo.count_by_type(UsageEventType.query),
        total_ingestions=await usage_repo.count_by_type(UsageEventType.ingestion),
        active_users_7d=await usage_repo.count_active_users_since(days_ago(7)),
        active_users_30d=await usage_repo.count_active_users_since(days_ago(30)),
    )


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(get_current_admin_user),
):
    user_repo = UserRepository(session)
    usage_repo = UsageEventRepository(session)

    users = await user_repo.list_all()
    return [
        AdminUserResponse(
            id=u.id,
            email=u.email,
            created_at=u.created_at,
            last_login_at=u.last_login_at,
            documents_ingested=await usage_repo.count_for_user(u.id, UsageEventType.ingestion),
            queries_sent=await usage_repo.count_for_user(u.id, UsageEventType.query),
            is_verified=u.is_verified,
            is_test_user=u.is_test_user,
        )
        for u in users
    ]


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: AdminCreateUserRequest,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(get_current_admin_user),
):
    user_repo = UserRepository(session)
    existing = await user_repo.get_by_email(body.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    hashed = hash_password(body.password)
    user = await user_repo.create_admin_user(email=body.email, hashed_password=hashed, is_test_user=body.is_test_user)
    logger.info(f"Admin created user — user_id={user.id} email={user.email} is_test_user={user.is_test_user}")

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        documents_ingested=0,
        queries_sent=0,
        is_verified=user.is_verified,
        is_test_user=user.is_test_user,
    )


@router.post("/users/{user_id}/verify")
async def verify_user(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(get_current_admin_user),
):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await user_repo.verify(user)
    logger.info(f"Admin verified user — user_id={user.id}")
    return {"message": "User verified"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    body: AdminDeleteUserRequest,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(get_current_admin_user),
):
    """Permanently delete a user and all their data. Irreversible.

    Requires the caller to type the exact email of the user being deleted —
    an AWS-style confirmation step to prevent accidental deletion.
    """
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.confirm_email != user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation email does not match — deletion cancelled.",
        )

    logger.warning(f"Admin deleting user — admin={admin.email} target_user_id={user.id} target_email={user.email}")
    await UserDeletionService(session).delete(user)
    return {"message": f"User {user.email} permanently deleted"}
