"""add_graph_config_to_virtual_agents

Revision ID: c3a7f2e1b456
Revises: ba58d1b9cea2
Create Date: 2026-02-17 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3a7f2e1b456"
down_revision: Union[str, None] = "ba58d1b9cea2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add graph_config JSON column for declarative graph agents."""
    op.add_column(
        "virtual_agents",
        sa.Column("graph_config", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Remove graph_config column."""
    op.drop_column("virtual_agents", "graph_config")
