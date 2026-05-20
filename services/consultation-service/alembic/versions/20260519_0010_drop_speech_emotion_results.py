"""drop deprecated speech emotion results table

Revision ID: 20260519_0010
Revises: 20260519_0009
Create Date: 2026-05-19 23:10:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260519_0010"
down_revision = "20260519_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "speech_emotion_results" not in existing_tables:
        return

    existing_indexes = {index["name"] for index in inspector.get_indexes("speech_emotion_results")}
    if op.f("ix_speech_emotion_results_consultation_session_id") in existing_indexes:
        op.drop_index(
            op.f("ix_speech_emotion_results_consultation_session_id"),
            table_name="speech_emotion_results",
        )
    if op.f("ix_speech_emotion_results_consultation_turn_id") in existing_indexes:
        op.drop_index(
            op.f("ix_speech_emotion_results_consultation_turn_id"),
            table_name="speech_emotion_results",
        )
    op.drop_table("speech_emotion_results")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "speech_emotion_results" in existing_tables:
        return

    op.create_table(
        "speech_emotion_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("consultation_turn_id", sa.String(length=36), nullable=False),
        sa.Column("consultation_session_id", sa.String(length=36), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("primary_label", sa.String(length=128), nullable=True),
        sa.Column("primary_score", sa.Float(), nullable=True),
        sa.Column("top3_payload", sa.JSON(), nullable=True),
        sa.Column("inference_status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["consultation_session_id"],
            ["consultation_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["consultation_turn_id"],
            ["consultation_turns.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "consultation_turn_id",
            name="uq_speech_emotion_results_consultation_turn_id",
        ),
    )
    op.create_index(
        op.f("ix_speech_emotion_results_consultation_turn_id"),
        "speech_emotion_results",
        ["consultation_turn_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_speech_emotion_results_consultation_session_id"),
        "speech_emotion_results",
        ["consultation_session_id"],
        unique=False,
    )
