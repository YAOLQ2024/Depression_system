"""align multimodal asr contract

Revision ID: 20260518_0003
Revises: 20260517_0002
Create Date: 2026-05-18 11:10:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260518_0003"
down_revision = "20260517_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "multimodal_sessions",
        sa.Column("owner_service", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "multimodal_sessions",
        sa.Column("stage_context", sa.JSON(), nullable=True),
    )
    op.add_column(
        "multimodal_sessions",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column(
        "multimodal_sessions",
        "owner_session_id",
        existing_type=sa.String(length=36),
        type_=sa.String(length=128),
        existing_nullable=False,
    )

    op.execute(
        """
        UPDATE multimodal_sessions
        SET owner_service = 'consultation-service',
            stage_context = '{}'::json,
            started_at = created_at
        WHERE owner_service IS NULL
        """
    )

    op.alter_column(
        "multimodal_sessions",
        "owner_service",
        existing_type=sa.String(length=128),
        nullable=False,
    )
    op.alter_column(
        "multimodal_sessions",
        "stage_context",
        existing_type=sa.JSON(),
        nullable=False,
    )
    op.alter_column(
        "multimodal_sessions",
        "started_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_multimodal_sessions_owner",
        "multimodal_sessions",
        ["owner_service", "owner_session_id"],
    )

    op.create_table(
        "multimodal_audio_turns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("multimodal_session_id", sa.String(length=36), nullable=False),
        sa.Column("consultation_session_id", sa.String(length=36), nullable=False),
        sa.Column("turn_id", sa.String(length=36), nullable=True),
        sa.Column("stage_id", sa.String(length=128), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=False),
        sa.Column("question_key", sa.String(length=128), nullable=False),
        sa.Column("prompt_key", sa.String(length=128), nullable=True),
        sa.Column("audio_uri", sa.Text(), nullable=False),
        sa.Column("storage_provider", sa.String(length=64), nullable=False),
        sa.Column("storage_object_key", sa.Text(), nullable=False),
        sa.Column("source_filename", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("processing_status", sa.String(length=64), nullable=False),
        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column("transcript_confidence", sa.Float(), nullable=True),
        sa.Column("asr_provider", sa.String(length=64), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("response_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
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
    op.create_index(
        op.f("ix_multimodal_audio_turns_turn_id"),
        "multimodal_audio_turns",
        ["turn_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_multimodal_audio_turns_turn_id"),
        table_name="multimodal_audio_turns",
    )
    op.drop_index(
        op.f("ix_multimodal_audio_turns_consultation_session_id"),
        table_name="multimodal_audio_turns",
    )
    op.drop_index(
        op.f("ix_multimodal_audio_turns_multimodal_session_id"),
        table_name="multimodal_audio_turns",
    )
    op.drop_table("multimodal_audio_turns")

    op.drop_constraint(
        "uq_multimodal_sessions_owner",
        "multimodal_sessions",
        type_="unique",
    )
    op.drop_column("multimodal_sessions", "started_at")
    op.drop_column("multimodal_sessions", "stage_context")
    op.drop_column("multimodal_sessions", "owner_service")
    op.alter_column(
        "multimodal_sessions",
        "owner_session_id",
        existing_type=sa.String(length=128),
        type_=sa.String(length=36),
        existing_nullable=False,
    )
