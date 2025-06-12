"""Remove obsolete virtual assistant tables

Revision ID: faafd4ce8f16
Revises: 7fc140ef6ec7
Create Date: 2025-06-02 14:01:33.051038

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "faafd4ce8f16"
down_revision: Union[str, None] = "7fc140ef6ec7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "chat_history_virtual_assistant_id_fkey", "chat_history", type_="foreignkey"
    )
    op.drop_table("virtual_assistant_tools")
    op.drop_table("virtual_assistant_knowledge_bases")
    op.drop_table("virtual_assistants")


def downgrade() -> None:
    op.create_table(
        "virtual_assistants",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("created_by", sa.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_table(
        "virtual_assistant_knowledge_bases",
        sa.Column(
            "virtual_assistant_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("virtual_assistants.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "vector_db_name",
            sa.String(length=255),
            sa.ForeignKey("knowledge_bases.vector_db_name"),
            primary_key=True,
        ),
    )
    op.create_table(
        "virtual_assistant_tools",
        sa.Column(
            "virtual_assistant_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("virtual_assistants.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("toolgroup_id", sa.String(length=255), primary_key=True),
    )
    op.create_foreign_key(
        "chat_history_virtual_assistant_id_fkey",
        "chat_history",
        "virtual_assistants",
        ["virtual_assistant_id"],
        ["id"],
        ondelete="CASCADE",
    )
