"""create multimodal storage tables

Revision ID: 20260517_0002
Revises: 20260504_0001
Create Date: 2026-05-17 18:10:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260517_0002"
down_revision = "20260504_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "multimodal_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("owner_session_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("enabled_modalities", sa.JSON(), nullable=False),
        sa.Column("latest_live_payload", sa.JSON(), nullable=True),
        sa.Column("session_summary_payload", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("warmed_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_multimodal_sessions_owner_session_id"), "multimodal_sessions", ["owner_session_id"], unique=False)
    op.create_index(op.f("ix_multimodal_sessions_user_id"), "multimodal_sessions", ["user_id"], unique=False)

    op.create_table(
        "multimodal_captures",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("consultation_turn_id", sa.String(length=36), nullable=True),
        sa.Column("modality", sa.String(length=64), nullable=False),
        sa.Column("capture_kind", sa.String(length=64), nullable=False),
        sa.Column("source_ref_id", sa.String(length=128), nullable=True),
        sa.Column("storage_uri", sa.String(length=512), nullable=True),
        sa.Column("capture_payload", sa.JSON(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["multimodal_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_multimodal_captures_consultation_turn_id"), "multimodal_captures", ["consultation_turn_id"], unique=False)
    op.create_index(op.f("ix_multimodal_captures_modality"), "multimodal_captures", ["modality"], unique=False)
    op.create_index(op.f("ix_multimodal_captures_session_id"), "multimodal_captures", ["session_id"], unique=False)

    op.create_table(
        "multimodal_inference_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("consultation_turn_id", sa.String(length=36), nullable=True),
        sa.Column("modality", sa.String(length=64), nullable=False),
        sa.Column("source_kind", sa.String(length=64), nullable=False),
        sa.Column("source_ref_id", sa.String(length=128), nullable=True),
        sa.Column("inference_payload", sa.JSON(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["multimodal_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_multimodal_inference_results_consultation_turn_id"), "multimodal_inference_results", ["consultation_turn_id"], unique=False)
    op.create_index(op.f("ix_multimodal_inference_results_modality"), "multimodal_inference_results", ["modality"], unique=False)
    op.create_index(op.f("ix_multimodal_inference_results_session_id"), "multimodal_inference_results", ["session_id"], unique=False)

    op.create_table(
        "multimodal_turn_bundles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("consultation_turn_id", sa.String(length=36), nullable=False),
        sa.Column("bundle_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["multimodal_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "consultation_turn_id", name="uq_multimodal_turn_bundles_session_turn"),
    )
    op.create_index(op.f("ix_multimodal_turn_bundles_consultation_turn_id"), "multimodal_turn_bundles", ["consultation_turn_id"], unique=False)
    op.create_index(op.f("ix_multimodal_turn_bundles_session_id"), "multimodal_turn_bundles", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_multimodal_turn_bundles_session_id"), table_name="multimodal_turn_bundles")
    op.drop_index(op.f("ix_multimodal_turn_bundles_consultation_turn_id"), table_name="multimodal_turn_bundles")
    op.drop_table("multimodal_turn_bundles")

    op.drop_index(op.f("ix_multimodal_inference_results_session_id"), table_name="multimodal_inference_results")
    op.drop_index(op.f("ix_multimodal_inference_results_modality"), table_name="multimodal_inference_results")
    op.drop_index(op.f("ix_multimodal_inference_results_consultation_turn_id"), table_name="multimodal_inference_results")
    op.drop_table("multimodal_inference_results")

    op.drop_index(op.f("ix_multimodal_captures_session_id"), table_name="multimodal_captures")
    op.drop_index(op.f("ix_multimodal_captures_modality"), table_name="multimodal_captures")
    op.drop_index(op.f("ix_multimodal_captures_consultation_turn_id"), table_name="multimodal_captures")
    op.drop_table("multimodal_captures")

    op.drop_index(op.f("ix_multimodal_sessions_user_id"), table_name="multimodal_sessions")
    op.drop_index(op.f("ix_multimodal_sessions_owner_session_id"), table_name="multimodal_sessions")
    op.drop_table("multimodal_sessions")
