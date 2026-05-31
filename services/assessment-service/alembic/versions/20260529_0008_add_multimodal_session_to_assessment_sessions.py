"""add multimodal session id to assessment sessions

Revision ID: 20260529_0008
Revises: 20260529_0007
Create Date: 2026-05-29 22:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260529_0008"
down_revision = "20260529_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessment_sessions",
        sa.Column("multimodal_session_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_assessment_sessions_multimodal_session_id"),
        "assessment_sessions",
        ["multimodal_session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_assessment_sessions_multimodal_session_id"),
        table_name="assessment_sessions",
    )
    op.drop_column("assessment_sessions", "multimodal_session_id")
