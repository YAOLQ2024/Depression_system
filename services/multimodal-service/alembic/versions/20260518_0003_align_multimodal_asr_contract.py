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
        sa.Column("owner_session_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "multimodal_sessions",
        sa.Column("stage_context", sa.JSON(), nullable=True),
    )
    op.add_column(
        "multimodal_sessions",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        """
        UPDATE multimodal_sessions
        SET owner_service = 'consultation-service',
            owner_session_id = consultation_session_id,
            stage_context = '{}'::json,
            started_at = created_at
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
        "owner_session_id",
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
    op.drop_index(
        op.f("ix_multimodal_sessions_consultation_session_id"),
        table_name="multimodal_sessions",
    )
    op.create_index(
        op.f("ix_multimodal_sessions_owner_session_id"),
        "multimodal_sessions",
        ["owner_session_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_multimodal_sessions_owner",
        "multimodal_sessions",
        ["owner_service", "owner_session_id"],
    )
    op.drop_column("multimodal_sessions", "workflow_id")
    op.drop_column("multimodal_sessions", "consultation_session_id")
    op.drop_column("multimodal_sessions", "created_at")

    op.add_column(
        "multimodal_audio_turns",
        sa.Column("turn_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "multimodal_audio_turns",
        sa.Column("stage_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "multimodal_audio_turns",
        sa.Column("node_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "multimodal_audio_turns",
        sa.Column("storage_object_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "multimodal_audio_turns",
        sa.Column("transcript_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "multimodal_audio_turns",
        sa.Column("transcript_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "multimodal_audio_turns",
        sa.Column("asr_provider", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "multimodal_audio_turns",
        sa.Column("error_code", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "multimodal_audio_turns",
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    op.execute(
        """
        UPDATE multimodal_audio_turns
        SET stage_id = 'legacy-stage',
            node_id = 'legacy-node',
            storage_object_key = stored_relative_path,
            asr_provider = 'dolphin',
            storage_provider = CASE
                WHEN storage_provider = 'runtime-assets-placeholder'
                THEN 'legacy-runtime-assets'
                ELSE storage_provider
            END,
            processing_status = CASE
                WHEN processing_status IN ('uploaded_pending_transcription', 'uploaded', 'transcribing')
                THEN 'failed'
                ELSE processing_status
            END,
            error_code = CASE
                WHEN processing_status IN ('uploaded_pending_transcription', 'uploaded', 'transcribing')
                THEN 'SERVICE_RESTARTED'
                ELSE error_code
            END,
            error_message = CASE
                WHEN processing_status IN ('uploaded_pending_transcription', 'uploaded', 'transcribing')
                THEN 'legacy placeholder transcription state was invalidated during migration'
                ELSE error_message
            END
        """
    )

    op.alter_column(
        "multimodal_audio_turns",
        "stage_id",
        existing_type=sa.String(length=128),
        nullable=False,
    )
    op.alter_column(
        "multimodal_audio_turns",
        "node_id",
        existing_type=sa.String(length=128),
        nullable=False,
    )
    op.alter_column(
        "multimodal_audio_turns",
        "storage_object_key",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.alter_column(
        "multimodal_audio_turns",
        "asr_provider",
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.create_index(
        op.f("ix_multimodal_audio_turns_turn_id"),
        "multimodal_audio_turns",
        ["turn_id"],
        unique=False,
    )
    op.drop_column("multimodal_audio_turns", "stored_relative_path")


def downgrade() -> None:
    op.add_column(
        "multimodal_audio_turns",
        sa.Column("stored_relative_path", sa.Text(), nullable=True),
    )
    op.execute(
        """
        UPDATE multimodal_audio_turns
        SET stored_relative_path = storage_object_key
        """
    )
    op.drop_index(
        op.f("ix_multimodal_audio_turns_turn_id"),
        table_name="multimodal_audio_turns",
    )
    op.drop_column("multimodal_audio_turns", "error_message")
    op.drop_column("multimodal_audio_turns", "error_code")
    op.drop_column("multimodal_audio_turns", "asr_provider")
    op.drop_column("multimodal_audio_turns", "transcript_confidence")
    op.drop_column("multimodal_audio_turns", "transcript_text")
    op.drop_column("multimodal_audio_turns", "storage_object_key")
    op.drop_column("multimodal_audio_turns", "node_id")
    op.drop_column("multimodal_audio_turns", "stage_id")
    op.drop_column("multimodal_audio_turns", "turn_id")
    op.alter_column(
        "multimodal_audio_turns",
        "stored_relative_path",
        existing_type=sa.Text(),
        nullable=False,
    )

    op.add_column(
        "multimodal_sessions",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "multimodal_sessions",
        sa.Column("consultation_session_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "multimodal_sessions",
        sa.Column("workflow_id", sa.String(length=128), nullable=True),
    )
    op.execute(
        """
        UPDATE multimodal_sessions
        SET consultation_session_id = LEFT(owner_session_id, 36),
            created_at = started_at
        """
    )
    op.drop_constraint(
        "uq_multimodal_sessions_owner",
        "multimodal_sessions",
        type_="unique",
    )
    op.drop_index(
        op.f("ix_multimodal_sessions_owner_session_id"),
        table_name="multimodal_sessions",
    )
    op.create_index(
        op.f("ix_multimodal_sessions_consultation_session_id"),
        "multimodal_sessions",
        ["consultation_session_id"],
        unique=True,
    )
    op.alter_column(
        "multimodal_sessions",
        "consultation_session_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )
    op.alter_column(
        "multimodal_sessions",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.drop_column("multimodal_sessions", "started_at")
    op.drop_column("multimodal_sessions", "stage_context")
    op.drop_column("multimodal_sessions", "owner_session_id")
    op.drop_column("multimodal_sessions", "owner_service")
