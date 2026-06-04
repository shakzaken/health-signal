"""add_content_hash_to_documents

Revision ID: 60ceed2a724e
Revises:
Create Date: 2026-06-04 10:25:46.564365

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '60ceed2a724e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('content_hash', sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column('documents', 'content_hash')
