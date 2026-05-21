"""add encounter scope fields to consultation tables

Revision ID: 20260520_0012
Revises: 20260520_0011
Create Date: 2026-05-20 21:20:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260520_0012"
down_revision = "20260520_0011"
branch_labels = None
depends_on = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _foreign_key_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {
        foreign_key["name"]
        for foreign_key in inspector.get_foreign_keys(table_name)
        if foreign_key.get("name")
    }


def _create_index_if_missing(
    inspector: sa.Inspector,
    table_name: str,
    index_name: str,
    columns: list[str],
) -> None:
    if index_name not in _index_names(inspector, table_name):
        op.create_index(index_name, table_name, columns, unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)

    if "encounter_sessions" not in existing_tables:
        op.create_table(
            "encounter_sessions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("entry_flow_type", sa.String(length=64), nullable=False),
            sa.Column("current_flow_type", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)
        existing_tables = _table_names(inspector)

    if "encounter_sessions" in existing_tables:
        _create_index_if_missing(
            inspector,
            "encounter_sessions",
            "ix_encounter_sessions_user_id",
            ["user_id"],
        )
        _create_index_if_missing(
            inspector,
            "encounter_sessions",
            "ix_encounter_sessions_status",
            ["status"],
        )

    if "consultation_sessions" in existing_tables:
        session_columns = _column_names(inspector, "consultation_sessions")
        if "encounter_session_id" not in session_columns:
            op.add_column(
                "consultation_sessions",
                sa.Column(
                    "encounter_session_id",
                    sa.String(length=36),
                    nullable=True,
                ),
            )
            inspector = sa.inspect(bind)
            session_columns = _column_names(inspector, "consultation_sessions")
        if "encounter_session_id" in session_columns:
            _create_index_if_missing(
                inspector,
                "consultation_sessions",
                "ix_consultation_sessions_encounter_session_id",
                ["encounter_session_id"],
            )
            foreign_keys = _foreign_key_names(inspector, "consultation_sessions")
            if (
                "fk_consultation_sessions_encounter_session_id"
                not in foreign_keys
            ):
                op.create_foreign_key(
                    "fk_consultation_sessions_encounter_session_id",
                    "consultation_sessions",
                    "encounter_sessions",
                    ["encounter_session_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
                inspector = sa.inspect(bind)

    if "consultation_turns" in existing_tables:
        turn_columns = _column_names(inspector, "consultation_turns")
        new_columns = (
            (
                "encounter_session_id",
                sa.Column(
                    "encounter_session_id",
                    sa.String(length=36),
                    nullable=True,
                ),
            ),
            (
                "consultation_flow_run_id",
                sa.Column(
                    "consultation_flow_run_id",
                    sa.String(length=36),
                    nullable=True,
                ),
            ),
            (
                "question_key",
                sa.Column("question_key", sa.String(length=128), nullable=True),
            ),
            (
                "question_order",
                sa.Column("question_order", sa.Integer(), nullable=True),
            ),
            (
                "question_video_asset_id",
                sa.Column(
                    "question_video_asset_id",
                    sa.String(length=128),
                    nullable=True,
                ),
            ),
            (
                "question_video_uri",
                sa.Column("question_video_uri", sa.Text(), nullable=True),
            ),
            (
                "question_text",
                sa.Column("question_text", sa.Text(), nullable=True),
            ),
            (
                "question_subtitle_text",
                sa.Column(
                    "question_subtitle_text",
                    sa.Text(),
                    nullable=True,
                ),
            ),
            (
                "turn_window_started_at",
                sa.Column(
                    "turn_window_started_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                ),
            ),
            (
                "turn_window_completed_at",
                sa.Column(
                    "turn_window_completed_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                ),
            ),
            (
                "turn_summary_payload",
                sa.Column("turn_summary_payload", sa.JSON(), nullable=True),
            ),
        )
        for column_name, column in new_columns:
            if column_name not in turn_columns:
                op.add_column("consultation_turns", column)
                inspector = sa.inspect(bind)
                turn_columns = _column_names(inspector, "consultation_turns")

        if "encounter_session_id" in turn_columns:
            _create_index_if_missing(
                inspector,
                "consultation_turns",
                "ix_consultation_turns_encounter_session_id",
                ["encounter_session_id"],
            )
        if "consultation_flow_run_id" in turn_columns:
            _create_index_if_missing(
                inspector,
                "consultation_turns",
                "ix_consultation_turns_consultation_flow_run_id",
                ["consultation_flow_run_id"],
            )
        if "question_key" in turn_columns:
            _create_index_if_missing(
                inspector,
                "consultation_turns",
                "ix_consultation_turns_question_key",
                ["question_key"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)

    if "consultation_turns" in existing_tables:
        turn_columns = _column_names(inspector, "consultation_turns")
        turn_indexes = _index_names(inspector, "consultation_turns")
        for index_name in (
            "ix_consultation_turns_question_key",
            "ix_consultation_turns_consultation_flow_run_id",
            "ix_consultation_turns_encounter_session_id",
        ):
            if index_name in turn_indexes:
                op.drop_index(index_name, table_name="consultation_turns")
        for column_name in (
            "turn_summary_payload",
            "turn_window_completed_at",
            "turn_window_started_at",
            "question_subtitle_text",
            "question_text",
            "question_video_uri",
            "question_video_asset_id",
            "question_order",
            "question_key",
            "consultation_flow_run_id",
            "encounter_session_id",
        ):
            if column_name in turn_columns:
                op.drop_column("consultation_turns", column_name)
                inspector = sa.inspect(bind)
                turn_columns = _column_names(inspector, "consultation_turns")

    if "consultation_sessions" in existing_tables:
        session_columns = _column_names(inspector, "consultation_sessions")
        session_indexes = _index_names(inspector, "consultation_sessions")
        session_foreign_keys = _foreign_key_names(
            inspector,
            "consultation_sessions",
        )
        if (
            "fk_consultation_sessions_encounter_session_id"
            in session_foreign_keys
        ):
            op.drop_constraint(
                "fk_consultation_sessions_encounter_session_id",
                "consultation_sessions",
                type_="foreignkey",
            )
        if "ix_consultation_sessions_encounter_session_id" in session_indexes:
            op.drop_index(
                "ix_consultation_sessions_encounter_session_id",
                table_name="consultation_sessions",
            )
        if "encounter_session_id" in session_columns:
            op.drop_column("consultation_sessions", "encounter_session_id")

    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)
    if "encounter_sessions" in existing_tables:
        encounter_indexes = _index_names(inspector, "encounter_sessions")
        for index_name in (
            "ix_encounter_sessions_status",
            "ix_encounter_sessions_user_id",
        ):
            if index_name in encounter_indexes:
                op.drop_index(index_name, table_name="encounter_sessions")
        op.drop_table("encounter_sessions")
