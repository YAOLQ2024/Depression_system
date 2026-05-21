"""add scope fields to multimodal tables

Revision ID: 20260520_0005
Revises: 20260519_0004
Create Date: 2026-05-20 21:20:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260520_0005"
down_revision = "20260519_0004"
branch_labels = None
depends_on = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _add_column_if_missing(
    inspector: sa.Inspector,
    table_name: str,
    column_name: str,
    column: sa.Column,
) -> sa.Inspector:
    if column_name not in _column_names(inspector, table_name):
        op.add_column(table_name, column)
        inspector = sa.inspect(op.get_bind())
    return inspector


def _create_index_if_missing(
    inspector: sa.Inspector,
    table_name: str,
    index_name: str,
    columns: list[str],
) -> sa.Inspector:
    if index_name not in _index_names(inspector, table_name):
        op.create_index(index_name, table_name, columns, unique=False)
        inspector = sa.inspect(op.get_bind())
    return inspector


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)

    if "multimodal_sessions" in existing_tables:
        inspector = _add_column_if_missing(
            inspector,
            "multimodal_sessions",
            "encounter_session_id",
            sa.Column("encounter_session_id", sa.String(length=36), nullable=True),
        )
        inspector = _add_column_if_missing(
            inspector,
            "multimodal_sessions",
            "flow_type",
            sa.Column("flow_type", sa.String(length=64), nullable=True),
        )
        inspector = _add_column_if_missing(
            inspector,
            "multimodal_sessions",
            "flow_run_id",
            sa.Column("flow_run_id", sa.String(length=36), nullable=True),
        )
        inspector = _add_column_if_missing(
            inspector,
            "multimodal_sessions",
            "live_state_payload",
            sa.Column("live_state_payload", sa.JSON(), nullable=True),
        )
        for index_name, columns in (
            (
                "ix_multimodal_sessions_encounter_session_id",
                ["encounter_session_id"],
            ),
            ("ix_multimodal_sessions_flow_type", ["flow_type"]),
            ("ix_multimodal_sessions_flow_run_id", ["flow_run_id"]),
        ):
            inspector = _create_index_if_missing(
                inspector,
                "multimodal_sessions",
                index_name,
                columns,
            )

    if "multimodal_captures" in existing_tables:
        for column_name, column in (
            ("turn_id", sa.Column("turn_id", sa.String(length=36), nullable=True)),
            (
                "flow_run_id",
                sa.Column("flow_run_id", sa.String(length=36), nullable=True),
            ),
            (
                "stage_id",
                sa.Column("stage_id", sa.String(length=128), nullable=True),
            ),
            (
                "question_key",
                sa.Column("question_key", sa.String(length=128), nullable=True),
            ),
            (
                "sample_index",
                sa.Column("sample_index", sa.Integer(), nullable=True),
            ),
            (
                "sample_started_at",
                sa.Column(
                    "sample_started_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                ),
            ),
            (
                "sample_ended_at",
                sa.Column(
                    "sample_ended_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                ),
            ),
        ):
            inspector = _add_column_if_missing(
                inspector,
                "multimodal_captures",
                column_name,
                column,
            )
        for index_name, columns in (
            ("ix_multimodal_captures_turn_id", ["turn_id"]),
            ("ix_multimodal_captures_flow_run_id", ["flow_run_id"]),
            ("ix_multimodal_captures_stage_id", ["stage_id"]),
            ("ix_multimodal_captures_question_key", ["question_key"]),
        ):
            inspector = _create_index_if_missing(
                inspector,
                "multimodal_captures",
                index_name,
                columns,
            )

    if "multimodal_inference_results" in existing_tables:
        for column_name, column in (
            ("turn_id", sa.Column("turn_id", sa.String(length=36), nullable=True)),
            (
                "flow_run_id",
                sa.Column("flow_run_id", sa.String(length=36), nullable=True),
            ),
            (
                "stage_id",
                sa.Column("stage_id", sa.String(length=128), nullable=True),
            ),
            (
                "question_key",
                sa.Column("question_key", sa.String(length=128), nullable=True),
            ),
            (
                "sample_id",
                sa.Column("sample_id", sa.String(length=36), nullable=True),
            ),
        ):
            inspector = _add_column_if_missing(
                inspector,
                "multimodal_inference_results",
                column_name,
                column,
            )
        for index_name, columns in (
            ("ix_multimodal_inference_results_turn_id", ["turn_id"]),
            ("ix_multimodal_inference_results_flow_run_id", ["flow_run_id"]),
            ("ix_multimodal_inference_results_stage_id", ["stage_id"]),
            ("ix_multimodal_inference_results_question_key", ["question_key"]),
            ("ix_multimodal_inference_results_sample_id", ["sample_id"]),
        ):
            inspector = _create_index_if_missing(
                inspector,
                "multimodal_inference_results",
                index_name,
                columns,
            )

    if "multimodal_turn_bundles" in existing_tables:
        for column_name, column in (
            ("turn_id", sa.Column("turn_id", sa.String(length=36), nullable=True)),
            (
                "flow_run_id",
                sa.Column("flow_run_id", sa.String(length=36), nullable=True),
            ),
            (
                "stage_id",
                sa.Column("stage_id", sa.String(length=128), nullable=True),
            ),
            (
                "question_key",
                sa.Column("question_key", sa.String(length=128), nullable=True),
            ),
        ):
            inspector = _add_column_if_missing(
                inspector,
                "multimodal_turn_bundles",
                column_name,
                column,
            )
        for index_name, columns in (
            ("ix_multimodal_turn_bundles_turn_id", ["turn_id"]),
            ("ix_multimodal_turn_bundles_flow_run_id", ["flow_run_id"]),
            ("ix_multimodal_turn_bundles_stage_id", ["stage_id"]),
            ("ix_multimodal_turn_bundles_question_key", ["question_key"]),
        ):
            inspector = _create_index_if_missing(
                inspector,
                "multimodal_turn_bundles",
                index_name,
                columns,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)

    if "multimodal_turn_bundles" in existing_tables:
        bundle_columns = _column_names(inspector, "multimodal_turn_bundles")
        bundle_indexes = _index_names(inspector, "multimodal_turn_bundles")
        for index_name in (
            "ix_multimodal_turn_bundles_question_key",
            "ix_multimodal_turn_bundles_stage_id",
            "ix_multimodal_turn_bundles_flow_run_id",
            "ix_multimodal_turn_bundles_turn_id",
        ):
            if index_name in bundle_indexes:
                op.drop_index(index_name, table_name="multimodal_turn_bundles")
        for column_name in (
            "question_key",
            "stage_id",
            "flow_run_id",
            "turn_id",
        ):
            if column_name in bundle_columns:
                op.drop_column("multimodal_turn_bundles", column_name)
                inspector = sa.inspect(bind)
                bundle_columns = _column_names(
                    inspector,
                    "multimodal_turn_bundles",
                )

    if "multimodal_inference_results" in existing_tables:
        result_columns = _column_names(inspector, "multimodal_inference_results")
        result_indexes = _index_names(
            inspector,
            "multimodal_inference_results",
        )
        for index_name in (
            "ix_multimodal_inference_results_sample_id",
            "ix_multimodal_inference_results_question_key",
            "ix_multimodal_inference_results_stage_id",
            "ix_multimodal_inference_results_flow_run_id",
            "ix_multimodal_inference_results_turn_id",
        ):
            if index_name in result_indexes:
                op.drop_index(
                    index_name,
                    table_name="multimodal_inference_results",
                )
        for column_name in (
            "sample_id",
            "question_key",
            "stage_id",
            "flow_run_id",
            "turn_id",
        ):
            if column_name in result_columns:
                op.drop_column("multimodal_inference_results", column_name)
                inspector = sa.inspect(bind)
                result_columns = _column_names(
                    inspector,
                    "multimodal_inference_results",
                )

    if "multimodal_captures" in existing_tables:
        capture_columns = _column_names(inspector, "multimodal_captures")
        capture_indexes = _index_names(inspector, "multimodal_captures")
        for index_name in (
            "ix_multimodal_captures_question_key",
            "ix_multimodal_captures_stage_id",
            "ix_multimodal_captures_flow_run_id",
            "ix_multimodal_captures_turn_id",
        ):
            if index_name in capture_indexes:
                op.drop_index(index_name, table_name="multimodal_captures")
        for column_name in (
            "sample_ended_at",
            "sample_started_at",
            "sample_index",
            "question_key",
            "stage_id",
            "flow_run_id",
            "turn_id",
        ):
            if column_name in capture_columns:
                op.drop_column("multimodal_captures", column_name)
                inspector = sa.inspect(bind)
                capture_columns = _column_names(
                    inspector,
                    "multimodal_captures",
                )

    if "multimodal_sessions" in existing_tables:
        session_columns = _column_names(inspector, "multimodal_sessions")
        session_indexes = _index_names(inspector, "multimodal_sessions")
        for index_name in (
            "ix_multimodal_sessions_flow_run_id",
            "ix_multimodal_sessions_flow_type",
            "ix_multimodal_sessions_encounter_session_id",
        ):
            if index_name in session_indexes:
                op.drop_index(index_name, table_name="multimodal_sessions")
        for column_name in (
            "live_state_payload",
            "flow_run_id",
            "flow_type",
            "encounter_session_id",
        ):
            if column_name in session_columns:
                op.drop_column("multimodal_sessions", column_name)
                inspector = sa.inspect(bind)
                session_columns = _column_names(
                    inspector,
                    "multimodal_sessions",
                )
