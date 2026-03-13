"""add token tracking to chat sessions

Revision ID: d06c20578e3c
Revises: c3a7f2e1b456
Create Date: 2026-03-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd06c20578e3c'
down_revision = 'c3a7f2e1b456'
branch_labels = None
depends_on = None


def upgrade():
    # Add token tracking columns to chat_sessions table
    op.add_column('chat_sessions', sa.Column('total_input_tokens', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('chat_sessions', sa.Column('total_output_tokens', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    # Remove token tracking columns
    op.drop_column('chat_sessions', 'total_output_tokens')
    op.drop_column('chat_sessions', 'total_input_tokens')
