"""add email verification to users

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-06-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("verification_token", sa.String(), nullable=True))
    op.add_column("users", sa.Column("verification_token_expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "verification_token_expires_at")
    op.drop_column("users", "verification_token")
    op.drop_column("users", "is_verified")
