from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from core.security import create_access_token, hash_password, verify_password
from db.session import get_session
from repositories.user_repository import UserRepository
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    existing = await repo.get_by_email(body.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    hashed = hash_password(body.password)
    user = await repo.create(email=body.email, hashed_password=hashed)
    logger.info(f"New user registered — user_id={user.id} email={user.email}")

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    user = await repo.get_by_email(body.email)
    # Return 401 for both "not found" and "wrong password" — avoids user enumeration
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    logger.info(f"User logged in — user_id={user.id}")
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)
