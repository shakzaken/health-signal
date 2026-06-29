import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from core.security import create_access_token, hash_password, verify_password
from db.session import get_session
from repositories.user_repository import UserRepository
from schemas.auth import LoginRequest, RegisterRequest, ResendVerificationRequest, TokenResponse
from services.email_service import EmailService

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

TOKEN_EXPIRY_HOURS = 24


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


def _token_expiry() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=TOKEN_EXPIRY_HOURS)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    existing = await repo.get_by_email(body.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    hashed = hash_password(body.password)

    if settings.environment != "production":
        # Skip email verification in non-production environments
        user = await repo.create(
            email=body.email,
            hashed_password=hashed,
            verification_token=None,
            verification_token_expires_at=None,
            is_verified=True,
        )
        logger.info(f"New user registered (dev, auto-verified) — user_id={user.id}")
        token = create_access_token(str(user.id))
        return TokenResponse(access_token=token)

    token = _generate_token()
    user = await repo.create(
        email=body.email,
        hashed_password=hashed,
        verification_token=token,
        verification_token_expires_at=_token_expiry(),
    )
    logger.info(f"New user registered — user_id={user.id} email={user.email}")

    email_service = EmailService()
    await email_service.send_verification_email(user.email, token)

    return {"message": "Registration successful. Please check your email to verify your account."}


@router.post("/verify-email", response_model=TokenResponse)
async def verify_email(
    token: str,
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    user = await repo.get_by_verification_token(token)

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification link")

    if user.verification_token_expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification link has expired. Please request a new one.")

    await repo.verify(user)
    logger.info(f"User verified — user_id={user.id}")

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.post("/resend-verification")
async def resend_verification(
    body: ResendVerificationRequest,
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    user = await repo.get_by_email(body.email)

    # Return 200 even if user not found — avoids email enumeration
    if not user or user.is_verified:
        return {"message": "If your account exists and is unverified, a new email has been sent."}

    token = _generate_token()
    await repo.set_verification_token(user, token, _token_expiry())

    email_service = EmailService()
    await email_service.send_verification_email(user.email, token)
    logger.info(f"Verification email resent — user_id={user.id}")

    return {"message": "If your account exists and is unverified, a new email has been sent."}


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

    if settings.environment == "production" and not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in.",
        )

    logger.info(f"User logged in — user_id={user.id}")
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)
