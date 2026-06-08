"""add_users_and_user_id_to_documents

Revision ID: a1b2c3d4e5f6
Revises: b3c4d5e6f7a8
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # Add user_id to documents (nullable with default "default" for existing rows)
    op.add_column(
        "documents",
        sa.Column("user_id", sa.Text(), nullable=True),
    )
    # Backfill existing rows with a sentinel value
    op.execute("UPDATE documents SET user_id = 'default' WHERE user_id IS NULL")


def downgrade() -> None:
    op.drop_column("documents", "user_id")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
