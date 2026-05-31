"""expand assessment answers for voice evidence

Revision ID: 20260529_0007
Revises: 20260521_0006
Create Date: 2026-05-29 16:30:00

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260529_0007"
down_revision = "20260521_0006"
branch_labels = None
depends_on = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)
    if "assessment_answers" not in existing_tables:
        return

    answer_columns = _column_names(inspector, "assessment_answers")

    columns_to_add = [
        ("question_key", sa.Column("question_key", sa.String(length=128), nullable=True)),
        ("turn_id", sa.Column("turn_id", sa.String(length=64), nullable=True)),
        ("answer_source", sa.Column("answer_source", sa.String(length=32), nullable=True)),
        ("transcript_text", sa.Column("transcript_text", sa.Text(), nullable=True)),
        ("transcript_source", sa.Column("transcript_source", sa.String(length=64), nullable=True)),
        ("audio_uri", sa.Column("audio_uri", sa.Text(), nullable=True)),
        ("original_audio_uri", sa.Column("original_audio_uri", sa.Text(), nullable=True)),
        ("normalized_wav_uri", sa.Column("normalized_wav_uri", sa.Text(), nullable=True)),
        ("multimodal_session_id", sa.Column("multimodal_session_id", sa.String(length=36), nullable=True)),
        ("selected_option_label", sa.Column("selected_option_label", sa.String(length=255), nullable=True)),
        ("selected_option_score", sa.Column("selected_option_score", sa.Integer(), nullable=True)),
        ("response_started_at", sa.Column("response_started_at", sa.DateTime(timezone=True), nullable=True)),
        ("response_completed_at", sa.Column("response_completed_at", sa.DateTime(timezone=True), nullable=True)),
    ]

    for column_name, column in columns_to_add:
        if column_name not in answer_columns:
            op.add_column("assessment_answers", column)
            inspector = sa.inspect(bind)
            answer_columns = _column_names(inspector, "assessment_answers")

    if {"selected_option_label", "normalized_option"}.issubset(answer_columns):
        op.execute(
            sa.text(
                """
                UPDATE assessment_answers
                SET selected_option_label = COALESCE(selected_option_label, normalized_option)
                """
            )
        )

    if {"selected_option_score", "score_value"}.issubset(answer_columns):
        op.execute(
            sa.text(
                """
                UPDATE assessment_answers
                SET selected_option_score = COALESCE(selected_option_score, score_value)
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)
    if "assessment_answers" not in existing_tables:
        return

    answer_columns = _column_names(inspector, "assessment_answers")

    columns_to_drop = [
        "response_completed_at",
        "response_started_at",
        "selected_option_score",
        "selected_option_label",
        "multimodal_session_id",
        "normalized_wav_uri",
        "original_audio_uri",
        "audio_uri",
        "transcript_source",
        "transcript_text",
        "answer_source",
        "turn_id",
        "question_key",
    ]

    for column_name in columns_to_drop:
        if column_name in answer_columns:
            op.drop_column("assessment_answers", column_name)
            inspector = sa.inspect(bind)
            answer_columns = _column_names(inspector, "assessment_answers")

