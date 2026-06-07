import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from repositories.conversation_repository import ConversationRepository
from schemas.conversation import ConversationMessageResponse, ConversationSessionResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])


class AppendMessageRequest(BaseModel):
    user_id: str = "default"
    role: str  # "user" | "assistant"
    content: str


class UpdateSummaryRequest(BaseModel):
    summary: str


class CompressMessagesResponse(BaseModel):
    messages: list[ConversationMessageResponse]


@router.get("/{session_id}", response_model=ConversationSessionResponse)
async def get_conversation_session(
    session_id: uuid.UUID,
    user_id: str = Query("default"),
    recent: int = Query(6, description="Number of recent messages to return verbatim"),
    session: AsyncSession = Depends(get_session),
):
    """Load a conversation session — summary + recent N messages + total message count."""
    repo = ConversationRepository(session)
    conv_session = await repo.get_or_create_session(session_id, user_id)
    recent_messages = await repo.get_recent_messages(session_id, limit=recent)
    total_count = await repo.count_messages(session_id)
    return ConversationSessionResponse(
        session_id=conv_session.session_id,
        user_id=conv_session.user_id,
        summary=conv_session.summary,
        updated_at=conv_session.updated_at,
        total_count=total_count,
        messages=[
            ConversationMessageResponse(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in recent_messages
        ],
    )


@router.post("/{session_id}/messages", response_model=ConversationMessageResponse)
async def append_message(
    session_id: uuid.UUID,
    request: AppendMessageRequest,
    session: AsyncSession = Depends(get_session),
):
    """Append one message to a session. Creates the session if it does not exist."""
    repo = ConversationRepository(session)
    await repo.get_or_create_session(session_id, request.user_id)
    msg = await repo.append_message(
        session_id=session_id,
        user_id=request.user_id,
        role=request.role,
        content=request.content,
    )
    return ConversationMessageResponse(
        id=msg.id,
        session_id=msg.session_id,
        role=msg.role,
        content=msg.content,
        created_at=msg.created_at,
    )


@router.put("/{session_id}/summary")
async def update_summary(
    session_id: uuid.UUID,
    request: UpdateSummaryRequest,
    session: AsyncSession = Depends(get_session),
):
    """Replace the rolling summary for a session."""
    repo = ConversationRepository(session)
    await repo.update_summary(session_id, request.summary)
    return {"status": "ok"}


@router.get("/{session_id}/to-compress", response_model=CompressMessagesResponse)
async def get_messages_to_compress(
    session_id: uuid.UUID,
    keep_last: int = Query(6, description="How many recent messages to keep verbatim"),
    session: AsyncSession = Depends(get_session),
):
    """Return messages older than the most recent `keep_last` — for LLM summarization."""
    repo = ConversationRepository(session)
    messages = await repo.get_messages_to_compress(session_id, keep_last=keep_last)
    return CompressMessagesResponse(
        messages=[
            ConversationMessageResponse(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in messages
        ]
    )
