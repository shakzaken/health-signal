import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_verification_token(self, token: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.verification_token == token)
        )
        return result.scalar_one_or_none()

    async def get_by_provider_id(self, provider: str, provider_user_id: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.provider == provider, User.provider_user_id == provider_user_id)
        )
        return result.scalar_one_or_none()

    async def create_google_user(self, email: str, provider_user_id: str) -> User:
        user = User(
            email=email,
            hashed_password=None,
            provider="google",
            provider_user_id=provider_user_id,
            is_verified=True,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def link_provider(self, user: User, provider: str, provider_user_id: str) -> None:
        user.provider = provider
        user.provider_user_id = provider_user_id
        user.is_verified = True
        await self.session.commit()

    async def create(self, email: str, hashed_password: str, verification_token: Optional[str], verification_token_expires_at: Optional[datetime], is_verified: bool = False) -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            is_verified=is_verified,
            verification_token=verification_token,
            verification_token_expires_at=verification_token_expires_at,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def verify(self, user: User) -> User:
        user.is_verified = True
        user.verification_token = None
        user.verification_token_expires_at = None
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def set_verification_token(self, user: User, token: str, expires_at: datetime) -> None:
        user.verification_token = token
        user.verification_token_expires_at = expires_at
        await self.session.commit()

    async def set_last_login(self, user: User) -> None:
        user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await self.session.commit()

    async def list_all(self, exclude_test_users: bool = True) -> list[User]:
        query = select(User).order_by(User.created_at.desc())
        if exclude_test_users:
            query = query.where(User.is_test_user.is_(False))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_all(self, exclude_test_users: bool = True) -> int:
        from sqlalchemy import func
        query = select(func.count()).select_from(User)
        if exclude_test_users:
            query = query.where(User.is_test_user.is_(False))
        result = await self.session.execute(query)
        return result.scalar_one()

    async def create_admin_user(self, email: str, hashed_password: str, is_test_user: bool) -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            is_verified=True,
            is_test_user=is_test_user,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
