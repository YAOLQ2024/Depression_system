"""add multimodal fields

Revision ID: 20260517_0005
Revises: 20260517_0004
Create Date: 2026-05-17 23:10:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260517_0005"
down_revision = "20260517_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    session_columns = {
        column["name"] for column in inspector.get_columns("consultation_sessions")
    }
    session_indexes = {
        index["name"] for index in inspector.get_indexes("consultation_sessions")
    }
    turn_columns = {
        column["name"] for column in inspector.get_columns("consultation_turns")
    }

    if "multimodal_session_id" not in session_columns:
        op.add_column(
            "consultation_sessions",
            sa.Column("multimodal_session_id", sa.String(length=36), nullable=True),
        )
    if "multimodal_live_payload" not in session_columns:
        op.add_column(
            "consultation_sessions",
            sa.Column("multimodal_live_payload", sa.JSON(), nullable=True),
        )
    if "multimodal_live_updated_at" not in session_columns:
        op.add_column(
            "consultation_sessions",
            sa.Column("multimodal_live_updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    session_index_name = op.f("ix_consultation_sessions_multimodal_session_id")
    if session_index_name not in session_indexes:
        op.create_index(
            session_index_name,
            "consultation_sessions",
            ["multimodal_session_id"],
            unique=False,
        )

    if "multimodal_bundle_payload" not in turn_columns:
        op.add_column(
            "consultation_turns",
            sa.Column("multimodal_bundle_payload", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    session_columns = {
        column["name"] for column in inspector.get_columns("consultation_sessions")
    }
    session_indexes = {
        index["name"] for index in inspector.get_indexes("consultation_sessions")
    }
    turn_columns = {
        column["name"] for column in inspector.get_columns("consultation_turns")
    }

    if "multimodal_bundle_payload" in turn_columns:
        op.drop_column("consultation_turns", "multimodal_bundle_payload")

    session_index_name = op.f("ix_consultation_sessions_multimodal_session_id")
    if session_index_name in session_indexes:
        op.drop_index(
            session_index_name,
            table_name="consultation_sessions",
        )
    if "multimodal_live_updated_at" in session_columns:
        op.drop_column("consultation_sessions", "multimodal_live_updated_at")
    if "multimodal_live_payload" in session_columns:
        op.drop_column("consultation_sessions", "multimodal_live_payload")
    if "multimodal_session_id" in session_columns:
        op.drop_column("consultation_sessions", "multimodal_session_id")
