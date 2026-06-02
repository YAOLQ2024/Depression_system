"""create risk evaluation tables

Revision ID: 20260602_0002
Revises: 20260504_0001
Create Date: 2026-06-02 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260602_0002"
down_revision = "20260504_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "risk_evaluations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("encounter_session_id", sa.String(length=36), nullable=True),
        sa.Column("consultation_session_id", sa.String(length=36), nullable=True),
        sa.Column("assessment_session_id", sa.String(length=36), nullable=True),
        sa.Column("multimodal_session_id", sa.String(length=36), nullable=True),
        sa.Column("workflow_id", sa.String(length=128), nullable=True),
        sa.Column("rule_set_id", sa.String(length=128), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("depression_score", sa.Float(), nullable=True),
        sa.Column("depression_severity", sa.String(length=64), nullable=True),
        sa.Column("safety_risk_level", sa.String(length=32), nullable=False),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("consultation_payload", sa.JSON(), nullable=True),
        sa.Column("assessment_payload", sa.JSON(), nullable=True),
        sa.Column("multimodal_payload", sa.JSON(), nullable=True),
        sa.Column("input_summary_payload", sa.JSON(), nullable=True),
        sa.Column("result_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_risk_evaluations_user_id"),
        "risk_evaluations",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_risk_evaluations_encounter_session_id"),
        "risk_evaluations",
        ["encounter_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_risk_evaluations_consultation_session_id"),
        "risk_evaluations",
        ["consultation_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_risk_evaluations_assessment_session_id"),
        "risk_evaluations",
        ["assessment_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_risk_evaluations_multimodal_session_id"),
        "risk_evaluations",
        ["multimodal_session_id"],
        unique=False,
    )

    op.create_table(
        "risk_triggers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("evaluation_id", sa.String(length=36), nullable=False),
        sa.Column("trigger_key", sa.String(length=128), nullable=False),
        sa.Column("trigger_source", sa.String(length=128), nullable=False),
        sa.Column("trigger_effect", sa.String(length=255), nullable=False),
        sa.Column("evidence_summary", sa.String(length=1024), nullable=True),
        sa.Column("evidence_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_id"],
            ["risk_evaluations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_risk_triggers_evaluation_id"),
        "risk_triggers",
        ["evaluation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_risk_triggers_evaluation_id"), table_name="risk_triggers")
    op.drop_table("risk_triggers")
    op.drop_index(
        op.f("ix_risk_evaluations_multimodal_session_id"),
        table_name="risk_evaluations",
    )
    op.drop_index(
        op.f("ix_risk_evaluations_assessment_session_id"),
        table_name="risk_evaluations",
    )
    op.drop_index(
        op.f("ix_risk_evaluations_consultation_session_id"),
        table_name="risk_evaluations",
    )
    op.drop_index(
        op.f("ix_risk_evaluations_encounter_session_id"),
        table_name="risk_evaluations",
    )
    op.drop_index(op.f("ix_risk_evaluations_user_id"), table_name="risk_evaluations")
    op.drop_table("risk_evaluations")
