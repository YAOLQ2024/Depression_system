"""add multimodal fields to assessment sessions

Revision ID: 20260603_0007
Revises: 20260529_0008
Create Date: 2026-06-03 19:30:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260603_0007"
down_revision = "20260529_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    session_columns = {
        column["name"] for column in inspector.get_columns("assessment_sessions")
    }
    session_indexes = {
        index["name"] for index in inspector.get_indexes("assessment_sessions")
    }

    if "multimodal_session_id" not in session_columns:
        op.add_column(
            "assessment_sessions",
            sa.Column("multimodal_session_id", sa.String(length=36), nullable=True),
        )
    if "multimodal_live_payload" not in session_columns:
        op.add_column(
            "assessment_sessions",
            sa.Column("multimodal_live_payload", sa.JSON(), nullable=True),
        )
    if "multimodal_live_updated_at" not in session_columns:
        op.add_column(
            "assessment_sessions",
            sa.Column("multimodal_live_updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    session_index_name = op.f("ix_assessment_sessions_multimodal_session_id")
    if session_index_name not in session_indexes:
        op.create_index(
            session_index_name,
            "assessment_sessions",
            ["multimodal_session_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    session_columns = {
        column["name"] for column in inspector.get_columns("assessment_sessions")
    }
    session_indexes = {
        index["name"] for index in inspector.get_indexes("assessment_sessions")
    }

    session_index_name = op.f("ix_assessment_sessions_multimodal_session_id")
    if session_index_name in session_indexes:
        op.drop_index(
            session_index_name,
            table_name="assessment_sessions",
        )
    if "multimodal_live_updated_at" in session_columns:
        op.drop_column("assessment_sessions", "multimodal_live_updated_at")
    if "multimodal_live_payload" in session_columns:
        op.drop_column("assessment_sessions", "multimodal_live_payload")
    if "multimodal_session_id" in session_columns:
        op.drop_column("assessment_sessions", "multimodal_session_id")
