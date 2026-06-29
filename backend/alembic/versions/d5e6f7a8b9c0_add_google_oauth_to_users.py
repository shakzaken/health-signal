"""add google oauth to users

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-06-29

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "hashed_password", nullable=True)
    op.add_column("users", sa.Column("provider", sa.String(), nullable=True))
    op.add_column("users", sa.Column("provider_user_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "provider_user_id")
    op.drop_column("users", "provider")
    op.alter_column("users", "hashed_password", nullable=False)
