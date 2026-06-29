import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ConversationMessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ConversationSessionResponse(BaseModel):
    session_id: uuid.UUID
    user_id: str
    summary: Optional[str]
    updated_at: datetime
    total_count: int = 0
    messages: list[ConversationMessageResponse] = []


class ConversationListItemResponse(BaseModel):
    session_id: uuid.UUID
    title: str
    updated_at: datetime
