"""create assessment tables

Revision ID: 20260504_0002
Revises: 20260504_0001
Create Date: 2026-05-04 00:30:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260504_0002"
down_revision = "20260504_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessment_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("consultation_session_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("required_scales", sa.JSON(), nullable=False),
        sa.Column("selected_scales", sa.JSON(), nullable=False),
        sa.Column("current_scale_slug", sa.String(length=128), nullable=True),
        sa.Column("current_item_index", sa.Integer(), nullable=False),
        sa.Column("scale_handoff_payload", sa.JSON(), nullable=True),
        sa.Column("capture_context", sa.JSON(), nullable=True),
        sa.Column("aggregate_payload", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assessment_sessions_consultation_session_id"), "assessment_sessions", ["consultation_session_id"], unique=False)
    op.create_index(op.f("ix_assessment_sessions_user_id"), "assessment_sessions", ["user_id"], unique=False)

    op.create_table(
        "assessment_answers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("scale_slug", sa.String(length=128), nullable=False),
        sa.Column("item_id", sa.String(length=128), nullable=False),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column("raw_input", sa.Text(), nullable=True),
        sa.Column("normalized_option", sa.String(length=255), nullable=False),
        sa.Column("score_value", sa.Integer(), nullable=False),
        sa.Column("capture_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["assessment_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "scale_slug", "item_id", name="uq_assessment_answers_session_scale_item"),
    )
    op.create_index(op.f("ix_assessment_answers_scale_slug"), "assessment_answers", ["scale_slug"], unique=False)
    op.create_index(op.f("ix_assessment_answers_session_id"), "assessment_answers", ["session_id"], unique=False)

    op.create_table(
        "assessment_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("scale_slug", sa.String(length=128), nullable=False),
        sa.Column("raw_score", sa.Integer(), nullable=False),
        sa.Column("derived_score", sa.Integer(), nullable=False),
        sa.Column("interpretation_level", sa.String(length=128), nullable=True),
        sa.Column("interpretation_label", sa.String(length=255), nullable=True),
        sa.Column("risk_flags", sa.JSON(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["assessment_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "scale_slug", name="uq_assessment_results_session_scale"),
    )
    op.create_index(op.f("ix_assessment_results_session_id"), "assessment_results", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_assessment_results_session_id"), table_name="assessment_results")
    op.drop_table("assessment_results")
    op.drop_index(op.f("ix_assessment_answers_session_id"), table_name="assessment_answers")
    op.drop_index(op.f("ix_assessment_answers_scale_slug"), table_name="assessment_answers")
    op.drop_table("assessment_answers")
    op.drop_index(op.f("ix_assessment_sessions_user_id"), table_name="assessment_sessions")
    op.drop_index(op.f("ix_assessment_sessions_consultation_session_id"), table_name="assessment_sessions")
    op.drop_table("assessment_sessions")
