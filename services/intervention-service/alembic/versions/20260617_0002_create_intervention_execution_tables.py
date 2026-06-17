"""create intervention execution tables

Revision ID: 20260617_0002
Revises: 20260504_0001
Create Date: 2026-06-17 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260617_0002"
down_revision = "20260504_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intervention_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("encounter_session_id", sa.String(length=36), nullable=True),
        sa.Column("consultation_session_id", sa.String(length=36), nullable=True),
        sa.Column("assessment_session_id", sa.String(length=36), nullable=True),
        sa.Column("plan_id", sa.String(length=36), nullable=True),
        sa.Column("risk_evaluation_id", sa.String(length=36), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_program_id", sa.String(length=128), nullable=True),
        sa.Column("current_program_title", sa.String(length=255), nullable=True),
        sa.Column("current_delivery_mode", sa.String(length=64), nullable=True),
        sa.Column("metadata_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_intervention_sessions_user_id"),
        "intervention_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_intervention_sessions_encounter_session_id"),
        "intervention_sessions",
        ["encounter_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_intervention_sessions_consultation_session_id"),
        "intervention_sessions",
        ["consultation_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_intervention_sessions_assessment_session_id"),
        "intervention_sessions",
        ["assessment_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_intervention_sessions_plan_id"),
        "intervention_sessions",
        ["plan_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_intervention_sessions_risk_evaluation_id"),
        "intervention_sessions",
        ["risk_evaluation_id"],
        unique=False,
    )

    op.create_table(
        "intervention_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("program_id", sa.String(length=128), nullable=True),
        sa.Column("program_title", sa.String(length=255), nullable=True),
        sa.Column("delivery_mode", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["intervention_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_intervention_events_session_id"),
        "intervention_events",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_intervention_events_user_id"),
        "intervention_events",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_intervention_events_user_id"), table_name="intervention_events")
    op.drop_index(op.f("ix_intervention_events_session_id"), table_name="intervention_events")
    op.drop_table("intervention_events")

    op.drop_index(
        op.f("ix_intervention_sessions_risk_evaluation_id"),
        table_name="intervention_sessions",
    )
    op.drop_index(
        op.f("ix_intervention_sessions_plan_id"),
        table_name="intervention_sessions",
    )
    op.drop_index(
        op.f("ix_intervention_sessions_assessment_session_id"),
        table_name="intervention_sessions",
    )
    op.drop_index(
        op.f("ix_intervention_sessions_consultation_session_id"),
        table_name="intervention_sessions",
    )
    op.drop_index(
        op.f("ix_intervention_sessions_encounter_session_id"),
        table_name="intervention_sessions",
    )
    op.drop_index(
        op.f("ix_intervention_sessions_user_id"),
        table_name="intervention_sessions",
    )
    op.drop_table("intervention_sessions")
