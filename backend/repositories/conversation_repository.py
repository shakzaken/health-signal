import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation import ConversationMessage, ConversationSession

RECENT_WINDOW = 6       # verbatim messages kept per query
COMPRESS_THRESHOLD = 14  # trigger summarization once total messages exceed this


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_session(
        self, session_id: uuid.UUID, user_id: str
    ) -> ConversationSession:
        result = await self.session.execute(
            select(ConversationSession).where(
                ConversationSession.session_id == session_id,
                ConversationSession.user_id == user_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        new_session = ConversationSession(session_id=session_id, user_id=user_id)
        self.session.add(new_session)
        await self.session.commit()
        await self.session.refresh(new_session)
        return new_session

    async def get_recent_messages(
        self, session_id: uuid.UUID, limit: int = RECENT_WINDOW
    ) -> list[ConversationMessage]:
        """Return the most recent `limit` messages in chronological order."""
        result = await self.session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
        return list(reversed(messages))

    async def count_messages(self, session_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
        )
        return result.scalar_one()

    async def get_messages_to_compress(
        self, session_id: uuid.UUID, keep_last: int = RECENT_WINDOW
    ) -> list[ConversationMessage]:
        """Return all messages except the most recent `keep_last` — these should be compressed into the summary."""
        result = await self.session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.asc())
        )
        all_messages = list(result.scalars().all())
        if len(all_messages) <= keep_last:
            return []
        return all_messages[:-keep_last]

    async def append_message(
        self,
        session_id: uuid.UUID,
        user_id: str,
        role: str,
        content: str,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
        )
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        return msg

    async def update_summary(self, session_id: uuid.UUID, summary: str) -> None:
        result = await self.session.execute(
            select(ConversationSession).where(
                ConversationSession.session_id == session_id
            )
        )
        session_obj = result.scalar_one_or_none()
        if session_obj:
            session_obj.summary = summary
            session_obj.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await self.session.commit()
