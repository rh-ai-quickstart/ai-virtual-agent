"""Slim users table to keycloak_id + agent_ids only.

Rename id -> keycloak_id and drop username, email, role columns.
Identity now comes from Keycloak tokens/Admin API.

Revision ID: e1a2b3c4d5f6
Revises: d06c20578e3c
Create Date: 2026-08-04
"""

import sqlalchemy as sa
from alembic import op

revision = "e1a2b3c4d5f6"
down_revision = "d06c20578e3c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop FK constraints that reference users.id before the rename
    op.drop_constraint(
        "guardrails_created_by_fkey", "guardrails", type_="foreignkey"
    )
    op.drop_constraint(
        "knowledge_bases_created_by_fkey", "knowledge_bases", type_="foreignkey"
    )
    op.drop_constraint(
        "chat_sessions_user_id_fkey", "chat_sessions", type_="foreignkey"
    )

    op.alter_column("users", "id", new_column_name="keycloak_id")

    # Recreate FK constraints pointing to users.keycloak_id
    op.create_foreign_key(
        "guardrails_created_by_fkey",
        "guardrails",
        "users",
        ["created_by"],
        ["keycloak_id"],
    )
    op.create_foreign_key(
        "knowledge_bases_created_by_fkey",
        "knowledge_bases",
        "users",
        ["created_by"],
        ["keycloak_id"],
    )
    op.create_foreign_key(
        "chat_sessions_user_id_fkey",
        "chat_sessions",
        "users",
        ["user_id"],
        ["keycloak_id"],
        ondelete="CASCADE",
    )

    op.drop_column("users", "username")
    op.drop_column("users", "email")
    op.drop_column("users", "role")
    op.drop_column("users", "created_at")
    op.drop_column("users", "updated_at")

    op.execute("DROP TYPE IF EXISTS role")


def downgrade() -> None:
    role_enum = sa.Enum("admin", "devops", "user", name="role", create_type=True)
    role_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "users",
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "role",
            role_enum,
            nullable=False,
            server_default="user",
        ),
    )
    op.add_column(
        "users", sa.Column("email", sa.String(255), nullable=False, server_default="")
    )
    op.add_column(
        "users",
        sa.Column("username", sa.String(255), nullable=False, server_default=""),
    )

    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    # Drop FK constraints before renaming the column back
    op.drop_constraint(
        "guardrails_created_by_fkey", "guardrails", type_="foreignkey"
    )
    op.drop_constraint(
        "knowledge_bases_created_by_fkey", "knowledge_bases", type_="foreignkey"
    )
    op.drop_constraint(
        "chat_sessions_user_id_fkey", "chat_sessions", type_="foreignkey"
    )

    op.alter_column("users", "keycloak_id", new_column_name="id")

    # Recreate FK constraints pointing to users.id
    op.create_foreign_key(
        "guardrails_created_by_fkey",
        "guardrails",
        "users",
        ["created_by"],
        ["id"],
    )
    op.create_foreign_key(
        "knowledge_bases_created_by_fkey",
        "knowledge_bases",
        "users",
        ["created_by"],
        ["id"],
    )
    op.create_foreign_key(
        "chat_sessions_user_id_fkey",
        "chat_sessions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
