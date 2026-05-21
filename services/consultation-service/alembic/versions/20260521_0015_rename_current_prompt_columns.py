"""Rename current_prompt_* columns to current_question_* on consultation sessions.

Revision ID: 20260521_0015
Revises: 20260521_0014
Create Date: 2026-05-21 14:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260521_0015"
down_revision = "20260521_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "consultation_sessions",
        "current_prompt_key",
        new_column_name="current_question_key",
        existing_type=sa.String(length=128),
        existing_nullable=True,
    )
    op.alter_column(
        "consultation_sessions",
        "current_prompt_order",
        new_column_name="current_question_order",
        existing_type=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "consultation_sessions",
        "current_prompt_video_asset_id",
        new_column_name="current_question_video_asset_id",
        existing_type=sa.String(length=128),
        existing_nullable=True,
    )
    op.alter_column(
        "consultation_sessions",
        "current_prompt_video_uri",
        new_column_name="current_question_video_uri",
        existing_type=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "consultation_sessions",
        "current_prompt_question_text",
        new_column_name="current_question_text",
        existing_type=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "consultation_sessions",
        "current_prompt_subtitle_text",
        new_column_name="current_question_subtitle_text",
        existing_type=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "consultation_sessions",
        "current_question_subtitle_text",
        new_column_name="current_prompt_subtitle_text",
        existing_type=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "consultation_sessions",
        "current_question_text",
        new_column_name="current_prompt_question_text",
        existing_type=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "consultation_sessions",
        "current_question_video_uri",
        new_column_name="current_prompt_video_uri",
        existing_type=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "consultation_sessions",
        "current_question_video_asset_id",
        new_column_name="current_prompt_video_asset_id",
        existing_type=sa.String(length=128),
        existing_nullable=True,
    )
    op.alter_column(
        "consultation_sessions",
        "current_question_order",
        new_column_name="current_prompt_order",
        existing_type=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "consultation_sessions",
        "current_question_key",
        new_column_name="current_prompt_key",
        existing_type=sa.String(length=128),
        existing_nullable=True,
    )
