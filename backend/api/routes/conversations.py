import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from db.session import get_session
from models.user import User
from repositories.conversation_repository import ConversationRepository
from schemas.conversation import ConversationListItemResponse, ConversationMessageResponse, ConversationSessionResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])


class AppendMessageRequest(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class UpdateSummaryRequest(BaseModel):
    summary: str


class CompressMessagesResponse(BaseModel):
    messages: list[ConversationMessageResponse]


@router.get("", response_model=list[ConversationListItemResponse])
async def list_conversations(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return all conversation sessions for the current user, ordered by most recent."""
    repo = ConversationRepository(session)
    sessions = await repo.get_sessions_for_user(str(current_user.id))
    return [
        ConversationListItemResponse(session_id=s.session_id, title=title, updated_at=s.updated_at)
        for s, title in sessions
    ]


@router.get("/{session_id}", response_model=ConversationSessionResponse)
async def get_conversation_session(
    session_id: uuid.UUID,
    recent: int = Query(6, description="Number of recent messages to return verbatim"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Load a conversation session — summary + recent N messages + total message count."""
    user_id = str(current_user.id)
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
    current_user: User = Depends(get_current_user),
):
    """Append one message to a session. Creates the session if it does not exist."""
    user_id = str(current_user.id)
    repo = ConversationRepository(session)
    await repo.get_or_create_session(session_id, user_id)
    msg = await repo.append_message(
        session_id=session_id,
        user_id=user_id,
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
