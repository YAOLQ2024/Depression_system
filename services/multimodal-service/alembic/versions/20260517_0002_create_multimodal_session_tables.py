"""create multimodal session tables

Revision ID: 20260517_0002
Revises: 20260504_0001
Create Date: 2026-05-17 22:25:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260517_0002"
down_revision = "20260504_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "multimodal_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "consultation_session_id", sa.String(length=36), nullable=False
        ),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("workflow_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("consultation_session_id"),
    )
    op.create_index(
        op.f("ix_multimodal_sessions_consultation_session_id"),
        "multimodal_sessions",
        ["consultation_session_id"],
        unique=True,
    )

    op.create_table(
        "multimodal_audio_turns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "multimodal_session_id", sa.String(length=36), nullable=False
        ),
        sa.Column(
            "consultation_session_id", sa.String(length=36), nullable=False
        ),
        sa.Column("question_key", sa.String(length=128), nullable=False),
        sa.Column("prompt_key", sa.String(length=128), nullable=True),
        sa.Column("audio_uri", sa.Text(), nullable=False),
        sa.Column("storage_provider", sa.String(length=64), nullable=False),
        sa.Column("stored_relative_path", sa.Text(), nullable=False),
        sa.Column("source_filename", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("processing_status", sa.String(length=64), nullable=False),
        sa.Column(
            "response_started_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "response_completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["multimodal_session_id"],
            ["multimodal_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_multimodal_audio_turns_multimodal_session_id"),
        "multimodal_audio_turns",
        ["multimodal_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_multimodal_audio_turns_consultation_session_id"),
        "multimodal_audio_turns",
        ["consultation_session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_multimodal_audio_turns_consultation_session_id"),
        table_name="multimodal_audio_turns",
    )
    op.drop_index(
        op.f("ix_multimodal_audio_turns_multimodal_session_id"),
        table_name="multimodal_audio_turns",
    )
    op.drop_table("multimodal_audio_turns")

    op.drop_index(
        op.f("ix_multimodal_sessions_consultation_session_id"),
        table_name="multimodal_sessions",
    )
    op.drop_table("multimodal_sessions")
