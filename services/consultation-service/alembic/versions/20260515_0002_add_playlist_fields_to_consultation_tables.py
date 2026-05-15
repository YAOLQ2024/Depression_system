"""add playlist fields to consultation tables

Revision ID: 20260515_0002
Revises: 20260430_0001
Create Date: 2026-05-15 17:20:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260515_0002"
down_revision = "20260430_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consultation_sessions", sa.Column("playlist_version", sa.String(length=128), nullable=True))
    op.add_column("consultation_sessions", sa.Column("current_prompt_key", sa.String(length=128), nullable=True))
    op.add_column("consultation_sessions", sa.Column("current_prompt_order", sa.Integer(), nullable=True))
    op.add_column("consultation_sessions", sa.Column("current_prompt_video_asset_id", sa.String(length=128), nullable=True))
    op.add_column("consultation_sessions", sa.Column("current_prompt_video_uri", sa.Text(), nullable=True))
    op.add_column("consultation_sessions", sa.Column("current_prompt_question_text", sa.Text(), nullable=True))
    op.add_column("consultation_sessions", sa.Column("current_prompt_subtitle_text", sa.Text(), nullable=True))
    op.add_column(
        "consultation_sessions",
        sa.Column("total_prompt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "consultation_sessions",
        sa.Column("completed_prompt_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.add_column("consultation_turns", sa.Column("turn_index", sa.Integer(), nullable=True))
    op.add_column("consultation_turns", sa.Column("prompt_key", sa.String(length=128), nullable=True))
    op.add_column("consultation_turns", sa.Column("prompt_order", sa.Integer(), nullable=True))
    op.add_column("consultation_turns", sa.Column("prompt_video_asset_id", sa.String(length=128), nullable=True))
    op.add_column("consultation_turns", sa.Column("prompt_video_uri", sa.Text(), nullable=True))
    op.add_column("consultation_turns", sa.Column("prompt_question_text", sa.Text(), nullable=True))
    op.add_column("consultation_turns", sa.Column("prompt_subtitle_text", sa.Text(), nullable=True))
    op.add_column("consultation_turns", sa.Column("response_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("consultation_turns", sa.Column("response_completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("consultation_turns", "response_completed_at")
    op.drop_column("consultation_turns", "response_started_at")
    op.drop_column("consultation_turns", "prompt_subtitle_text")
    op.drop_column("consultation_turns", "prompt_question_text")
    op.drop_column("consultation_turns", "prompt_video_uri")
    op.drop_column("consultation_turns", "prompt_video_asset_id")
    op.drop_column("consultation_turns", "prompt_order")
    op.drop_column("consultation_turns", "prompt_key")
    op.drop_column("consultation_turns", "turn_index")

    op.drop_column("consultation_sessions", "completed_prompt_count")
    op.drop_column("consultation_sessions", "total_prompt_count")
    op.drop_column("consultation_sessions", "current_prompt_subtitle_text")
    op.drop_column("consultation_sessions", "current_prompt_question_text")
    op.drop_column("consultation_sessions", "current_prompt_video_uri")
    op.drop_column("consultation_sessions", "current_prompt_video_asset_id")
    op.drop_column("consultation_sessions", "current_prompt_order")
    op.drop_column("consultation_sessions", "current_prompt_key")
    op.drop_column("consultation_sessions", "playlist_version")
