"""Drop legacy multimodal columns and constraints after Step 7 hard cut.

Revision ID: 20260521_0009
Revises: 20260521_0008
Create Date: 2026-05-21 12:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260521_0009"
down_revision = "20260521_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_multimodal_turn_bundles_session_turn",
        "multimodal_turn_bundles",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_multimodal_turn_bundles_session_turn",
        "multimodal_turn_bundles",
        ["session_id", "turn_id"],
    )
    op.alter_column(
        "multimodal_turn_bundles",
        "turn_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )
    op.drop_index(
        op.f("ix_multimodal_turn_bundles_consultation_turn_id"),
        table_name="multimodal_turn_bundles",
    )
    op.drop_column("multimodal_turn_bundles", "consultation_turn_id")

    op.drop_index(
        op.f("ix_multimodal_captures_consultation_turn_id"),
        table_name="multimodal_captures",
    )
    op.drop_column("multimodal_captures", "consultation_turn_id")

    op.drop_index(
        op.f("ix_multimodal_inference_results_consultation_turn_id"),
        table_name="multimodal_inference_results",
    )
    op.drop_column("multimodal_inference_results", "consultation_turn_id")

    op.drop_index(
        op.f("ix_multimodal_audio_turns_consultation_session_id"),
        table_name="multimodal_audio_turns",
    )
    op.drop_column("multimodal_audio_turns", "consultation_session_id")
    op.drop_column("multimodal_audio_turns", "prompt_key")
    op.alter_column(
        "multimodal_audio_turns",
        "flow_run_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )

    op.drop_constraint(
        "uq_multimodal_sessions_owner",
        "multimodal_sessions",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_multimodal_sessions_flow_scope",
        "multimodal_sessions",
        ["flow_type", "flow_run_id"],
    )
    op.alter_column(
        "multimodal_sessions",
        "flow_type",
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.alter_column(
        "multimodal_sessions",
        "flow_run_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )
    op.drop_index(
        op.f("ix_multimodal_sessions_owner_session_id"),
        table_name="multimodal_sessions",
    )
    op.drop_column("multimodal_sessions", "owner_service")
    op.drop_column("multimodal_sessions", "owner_session_id")
    op.drop_column("multimodal_sessions", "consultation_session_id")
    op.drop_column("multimodal_sessions", "latest_live_payload")
    op.drop_column("multimodal_sessions", "session_summary_payload")


def downgrade() -> None:
    op.add_column(
        "multimodal_sessions",
        sa.Column("session_summary_payload", sa.JSON(), nullable=True),
    )
    op.add_column(
        "multimodal_sessions",
        sa.Column("latest_live_payload", sa.JSON(), nullable=True),
    )
    op.add_column(
        "multimodal_sessions",
        sa.Column("consultation_session_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "multimodal_sessions",
        sa.Column("owner_session_id", sa.String(length=128), nullable=False, server_default=""),
    )
    op.add_column(
        "multimodal_sessions",
        sa.Column("owner_service", sa.String(length=128), nullable=False, server_default="consultation-service"),
    )
    op.create_index(
        op.f("ix_multimodal_sessions_owner_session_id"),
        "multimodal_sessions",
        ["owner_session_id"],
        unique=False,
    )
    op.drop_constraint(
        "uq_multimodal_sessions_flow_scope",
        "multimodal_sessions",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_multimodal_sessions_owner",
        "multimodal_sessions",
        ["owner_service", "owner_session_id"],
    )
    op.alter_column(
        "multimodal_sessions",
        "flow_run_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )
    op.alter_column(
        "multimodal_sessions",
        "flow_type",
        existing_type=sa.String(length=64),
        nullable=True,
    )
    op.alter_column("multimodal_sessions", "owner_service", server_default=None)
    op.alter_column("multimodal_sessions", "owner_session_id", server_default=None)

    op.alter_column(
        "multimodal_audio_turns",
        "flow_run_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )
    op.add_column(
        "multimodal_audio_turns",
        sa.Column("prompt_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "multimodal_audio_turns",
        sa.Column("consultation_session_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_multimodal_audio_turns_consultation_session_id"),
        "multimodal_audio_turns",
        ["consultation_session_id"],
        unique=False,
    )

    op.add_column(
        "multimodal_inference_results",
        sa.Column("consultation_turn_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_multimodal_inference_results_consultation_turn_id"),
        "multimodal_inference_results",
        ["consultation_turn_id"],
        unique=False,
    )

    op.add_column(
        "multimodal_captures",
        sa.Column("consultation_turn_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_multimodal_captures_consultation_turn_id"),
        "multimodal_captures",
        ["consultation_turn_id"],
        unique=False,
    )

    op.add_column(
        "multimodal_turn_bundles",
        sa.Column("consultation_turn_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_multimodal_turn_bundles_consultation_turn_id"),
        "multimodal_turn_bundles",
        ["consultation_turn_id"],
        unique=False,
    )
    op.drop_constraint(
        "uq_multimodal_turn_bundles_session_turn",
        "multimodal_turn_bundles",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_multimodal_turn_bundles_session_turn",
        "multimodal_turn_bundles",
        ["session_id", "consultation_turn_id"],
    )
    op.alter_column(
        "multimodal_turn_bundles",
        "turn_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )
