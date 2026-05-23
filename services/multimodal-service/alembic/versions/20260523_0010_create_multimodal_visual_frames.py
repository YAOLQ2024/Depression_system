"""create shared visual frame table for multimodal visual input

Revision ID: 20260523_0010
Revises: 20260521_0009
Create Date: 2026-05-23 18:55:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260523_0010"
down_revision = "20260521_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "multimodal_visual_frames",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("turn_id", sa.String(length=36), nullable=True),
        sa.Column("flow_run_id", sa.String(length=36), nullable=True),
        sa.Column("stage_id", sa.String(length=128), nullable=True),
        sa.Column("question_key", sa.String(length=128), nullable=True),
        sa.Column("sample_index", sa.Integer(), nullable=True),
        sa.Column("sample_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sample_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("storage_uri", sa.String(length=512), nullable=True),
        sa.Column("capture_payload", sa.JSON(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["multimodal_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_multimodal_visual_frames_session_id"),
        "multimodal_visual_frames",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_multimodal_visual_frames_turn_id"),
        "multimodal_visual_frames",
        ["turn_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_multimodal_visual_frames_flow_run_id"),
        "multimodal_visual_frames",
        ["flow_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_multimodal_visual_frames_stage_id"),
        "multimodal_visual_frames",
        ["stage_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_multimodal_visual_frames_question_key"),
        "multimodal_visual_frames",
        ["question_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_multimodal_visual_frames_question_key"),
        table_name="multimodal_visual_frames",
    )
    op.drop_index(
        op.f("ix_multimodal_visual_frames_stage_id"),
        table_name="multimodal_visual_frames",
    )
    op.drop_index(
        op.f("ix_multimodal_visual_frames_flow_run_id"),
        table_name="multimodal_visual_frames",
    )
    op.drop_index(
        op.f("ix_multimodal_visual_frames_turn_id"),
        table_name="multimodal_visual_frames",
    )
    op.drop_index(
        op.f("ix_multimodal_visual_frames_session_id"),
        table_name="multimodal_visual_frames",
    )
    op.drop_table("multimodal_visual_frames")
