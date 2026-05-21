"""Add canonical flow_run_id to multimodal audio turns for Step 7 hard cut.

Revision ID: 20260521_0008
Revises: 20260521_0007
Create Date: 2026-05-21 11:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260521_0008"
down_revision = "20260521_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "multimodal_audio_turns",
        sa.Column("flow_run_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_multimodal_audio_turns_flow_run_id"),
        "multimodal_audio_turns",
        ["flow_run_id"],
        unique=False,
    )
    op.alter_column(
        "multimodal_audio_turns",
        "consultation_session_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "multimodal_audio_turns",
        "consultation_session_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )
    op.drop_index(
        op.f("ix_multimodal_audio_turns_flow_run_id"),
        table_name="multimodal_audio_turns",
    )
    op.drop_column("multimodal_audio_turns", "flow_run_id")
