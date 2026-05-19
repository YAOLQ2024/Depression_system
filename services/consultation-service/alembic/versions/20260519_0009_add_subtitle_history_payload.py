"""add subtitle_history_payload to consultation_sessions

Revision ID: 20260519_0009
Revises: 20260519_0008
Create Date: 2026-05-19 18:40:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260519_0009"
down_revision = "20260519_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "consultation_sessions" not in existing_tables:
        return

    session_columns = {
        column["name"] for column in inspector.get_columns("consultation_sessions")
    }
    if "subtitle_history_payload" not in session_columns:
        op.add_column(
            "consultation_sessions",
            sa.Column("subtitle_history_payload", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "consultation_sessions" not in existing_tables:
        return

    session_columns = {
        column["name"] for column in inspector.get_columns("consultation_sessions")
    }
    if "subtitle_history_payload" in session_columns:
        op.drop_column("consultation_sessions", "subtitle_history_payload")
