"""add multimodal fields

Revision ID: 20260517_0004
Revises: 20260516_0003
Create Date: 2026-05-17 23:10:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260517_0004"
down_revision = "20260516_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "consultation_sessions",
        sa.Column("multimodal_session_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "consultation_sessions",
        sa.Column("multimodal_live_payload", sa.JSON(), nullable=True),
    )
    op.add_column(
        "consultation_sessions",
        sa.Column("multimodal_live_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_consultation_sessions_multimodal_session_id"),
        "consultation_sessions",
        ["multimodal_session_id"],
        unique=False,
    )

    op.add_column(
        "consultation_turns",
        sa.Column("multimodal_bundle_payload", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("consultation_turns", "multimodal_bundle_payload")

    op.drop_index(
        op.f("ix_consultation_sessions_multimodal_session_id"),
        table_name="consultation_sessions",
    )
    op.drop_column("consultation_sessions", "multimodal_live_updated_at")
    op.drop_column("consultation_sessions", "multimodal_live_payload")
    op.drop_column("consultation_sessions", "multimodal_session_id")
