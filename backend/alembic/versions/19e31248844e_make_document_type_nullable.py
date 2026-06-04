"""make_document_type_nullable

Revision ID: 19e31248844e
Revises: 60ceed2a724e
Create Date: 2026-06-04 12:05:41.422500

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '19e31248844e'
down_revision: Union[str, Sequence[str], None] = '60ceed2a724e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('documents', 'document_type', nullable=True)


def downgrade() -> None:
    op.alter_column('documents', 'document_type', nullable=False)
