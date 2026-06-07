import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ConversationSession(Base):
    """One row per conversation session. Holds the rolling summary of older messages."""

    __tablename__ = "conversation_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, default="default")
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )


class ConversationMessage(Base):
    """Individual message in a conversation session."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversation_sessions.session_id")
    )
    user_id: Mapped[str] = mapped_column(String, default="default")
    role: Mapped[str] = mapped_column(String)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
