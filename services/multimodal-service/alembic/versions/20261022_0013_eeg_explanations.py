"""Persist asynchronous EEG explanation tasks and history.

Revision ID: 20261022_0013
Revises: 20260529_0012
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_0013"
down_revision = "20260529_0012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "multimodal_eeg_explanations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("multimodal_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sample_id", sa.String(36), sa.ForeignKey("multimodal_captures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inference_id", sa.String(36), sa.ForeignKey("multimodal_inference_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cache_key", sa.String(64), unique=True, nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("target_class", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("config_payload", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("lease_token", sa.String(36), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )
    op.create_index("ix_eeg_explanations_history", "multimodal_eeg_explanations", ["session_id", "created_at", "id"])
    op.create_index("ix_eeg_explanations_queue", "multimodal_eeg_explanations", ["status", "lease_expires_at"])
    op.create_index("ix_multimodal_eeg_explanations_config_hash", "multimodal_eeg_explanations", ["config_hash"])


def downgrade():
    op.drop_table("multimodal_eeg_explanations")
