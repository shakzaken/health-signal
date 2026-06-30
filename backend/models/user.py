import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)
    provider_user_id: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    is_verified: Mapped[bool] = mapped_column(default=False)
    verification_token: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)
    verification_token_expires_at: Mapped[Optional[datetime]] = mapped_column(default=None, nullable=True)
    is_test_user: Mapped[bool] = mapped_column(default=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(default=None, nullable=True)
