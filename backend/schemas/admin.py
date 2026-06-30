import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class AdminStatsResponse(BaseModel):
    total_users: int
    total_queries: int
    total_ingestions: int
    active_users_7d: int
    active_users_30d: int


class AdminUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    created_at: datetime
    last_login_at: Optional[datetime]
    documents_ingested: int
    queries_sent: int
    is_verified: bool
    is_test_user: bool


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    is_test_user: bool = False


class AdminDeleteUserRequest(BaseModel):
    confirm_email: str
