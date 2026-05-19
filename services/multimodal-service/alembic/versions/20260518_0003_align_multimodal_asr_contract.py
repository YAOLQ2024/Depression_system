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

    op.alter_column(
        "multimodal_audio_turns",
        "stored_relative_path",
        existing_type=sa.Text(),
        new_column_name="storage_object_key",
    )
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
        SET stage_id = COALESCE(stage_id, 'legacy'),
            node_id = COALESCE(node_id, 'legacy'),
            asr_provider = COALESCE(asr_provider, 'dolphin')
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


def downgrade() -> None:
    op.drop_index(
        op.f("ix_multimodal_audio_turns_turn_id"),
        table_name="multimodal_audio_turns",
    )
    op.drop_column("multimodal_audio_turns", "error_message")
    op.drop_column("multimodal_audio_turns", "error_code")
    op.drop_column("multimodal_audio_turns", "asr_provider")
    op.drop_column("multimodal_audio_turns", "transcript_confidence")
    op.drop_column("multimodal_audio_turns", "transcript_text")
    op.drop_column("multimodal_audio_turns", "node_id")
    op.drop_column("multimodal_audio_turns", "stage_id")
    op.drop_column("multimodal_audio_turns", "turn_id")
    op.alter_column(
        "multimodal_audio_turns",
        "storage_object_key",
        existing_type=sa.Text(),
        new_column_name="stored_relative_path",
    )

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
