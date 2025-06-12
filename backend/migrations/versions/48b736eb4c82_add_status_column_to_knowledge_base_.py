"""Add status column to Knowledge Base table

Revision ID: 48b736eb4c82
Revises: f68eca5850f7
Create Date: 2025-06-12 11:40:45.835903

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48b736eb4c82'
down_revision: Union[str, None] = 'f68eca5850f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('knowledge_bases', sa.Column('status', sa.String(length=50), autoincrement=False, nullable=True))
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('knowledge_bases', 'status')
    pass
