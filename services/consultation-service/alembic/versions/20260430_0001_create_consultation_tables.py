"""create consultation tables

Revision ID: 20260430_0001
Revises: None
Create Date: 2026-04-30 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260430_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consultation_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=128), nullable=False),
        sa.Column("script_bundle", sa.String(length=128), nullable=False),
        sa.Column("workflow_stage_id", sa.String(length=128), nullable=False),
        sa.Column("current_stage_id", sa.String(length=128), nullable=True),
        sa.Column("current_node_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("assigned_doctor_persona", sa.String(length=128), nullable=False),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("participant_profile_snapshot", sa.JSON(), nullable=False),
        sa.Column("context_snapshot", sa.JSON(), nullable=False),
        sa.Column("slot_values", sa.JSON(), nullable=False),
        sa.Column("engine_state", sa.JSON(), nullable=False),
        sa.Column("chief_complaint_raw_text", sa.Text(), nullable=True),
        sa.Column("chief_complaint_summary", sa.Text(), nullable=True),
        sa.Column("current_history_structured_result", sa.JSON(), nullable=True),
        sa.Column("high_risk_screening_result", sa.JSON(), nullable=True),
        sa.Column("scale_handoff_payload", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consultation_sessions_user_id", "consultation_sessions", ["user_id"], unique=False)
    op.create_index("ix_consultation_sessions_status", "consultation_sessions", ["status"], unique=False)

    op.create_table(
        "consultation_turns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_stage_id", sa.String(length=128), nullable=False),
        sa.Column("stage_id", sa.String(length=128), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=False),
        sa.Column("input_type", sa.String(length=64), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column("raw_input", sa.Text(), nullable=True),
        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column("structured_fields", sa.JSON(), nullable=True),
        sa.Column("branch_taken", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["consultation_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consultation_turns_session_id", "consultation_turns", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_consultation_turns_session_id", table_name="consultation_turns")
    op.drop_table("consultation_turns")
    op.drop_index("ix_consultation_sessions_status", table_name="consultation_sessions")
    op.drop_index("ix_consultation_sessions_user_id", table_name="consultation_sessions")
    op.drop_table("consultation_sessions")
