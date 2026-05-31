"""add encounter scope and origin flow type

Revision ID: 20260529_0011
Revises: 20260523_0010
Create Date: 2026-05-29 16:40:00

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260529_0011"
down_revision = "20260523_0010"
branch_labels = None
depends_on = None


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _unique_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table_name)}


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

    inspector = _add_column_if_missing(
        inspector,
        "multimodal_sessions",
        "scope_type",
        sa.Column("scope_type", sa.String(length=64), nullable=True),
    )
    inspector = _add_column_if_missing(
        inspector,
        "multimodal_sessions",
        "scope_id",
        sa.Column("scope_id", sa.String(length=36), nullable=True),
    )
    inspector = _create_index_if_missing(
        inspector,
        "multimodal_sessions",
        "ix_multimodal_sessions_scope_type",
        ["scope_type"],
    )
    inspector = _create_index_if_missing(
        inspector,
        "multimodal_sessions",
        "ix_multimodal_sessions_scope_id",
        ["scope_id"],
    )
    if "uq_multimodal_sessions_scope" not in _unique_names(
        inspector, "multimodal_sessions"
    ):
        op.create_unique_constraint(
            "uq_multimodal_sessions_scope",
            "multimodal_sessions",
            ["scope_type", "scope_id"],
        )
        inspector = sa.inspect(bind)

    for table_name in (
        "multimodal_audio_turns",
        "multimodal_captures",
        "multimodal_visual_frames",
        "multimodal_turn_bundles",
        "multimodal_inference_results",
    ):
        inspector = _add_column_if_missing(
            inspector,
            table_name,
            "origin_flow_type",
            sa.Column("origin_flow_type", sa.String(length=64), nullable=True),
        )
        inspector = _create_index_if_missing(
            inspector,
            table_name,
            f"ix_{table_name}_origin_flow_type",
            ["origin_flow_type"],
        )

    op.execute(
        sa.text(
            """
            UPDATE multimodal_sessions
            SET scope_type = COALESCE(NULLIF(scope_type, ''), 'flow'),
                scope_id = COALESCE(NULLIF(scope_id, ''), NULLIF(flow_run_id, ''))
            WHERE scope_type IS NULL OR scope_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE multimodal_audio_turns
            SET origin_flow_type = COALESCE(NULLIF(origin_flow_type, ''), 'consultation')
            WHERE origin_flow_type IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE multimodal_captures
            SET origin_flow_type = COALESCE(NULLIF(origin_flow_type, ''), 'consultation')
            WHERE origin_flow_type IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE multimodal_visual_frames
            SET origin_flow_type = COALESCE(NULLIF(origin_flow_type, ''), 'consultation')
            WHERE origin_flow_type IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE multimodal_turn_bundles
            SET origin_flow_type = COALESCE(NULLIF(origin_flow_type, ''), 'consultation')
            WHERE origin_flow_type IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE multimodal_inference_results
            SET origin_flow_type = COALESCE(NULLIF(origin_flow_type, ''), 'consultation')
            WHERE origin_flow_type IS NULL
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in (
        "multimodal_inference_results",
        "multimodal_turn_bundles",
        "multimodal_visual_frames",
        "multimodal_captures",
        "multimodal_audio_turns",
    ):
        if f"ix_{table_name}_origin_flow_type" in _index_names(inspector, table_name):
            op.drop_index(f"ix_{table_name}_origin_flow_type", table_name=table_name)
            inspector = sa.inspect(bind)
        if "origin_flow_type" in _column_names(inspector, table_name):
            op.drop_column(table_name, "origin_flow_type")
            inspector = sa.inspect(bind)

    if "uq_multimodal_sessions_scope" in _unique_names(inspector, "multimodal_sessions"):
        op.drop_constraint(
            "uq_multimodal_sessions_scope",
            "multimodal_sessions",
            type_="unique",
        )
        inspector = sa.inspect(bind)
    for index_name in ("ix_multimodal_sessions_scope_id", "ix_multimodal_sessions_scope_type"):
        if index_name in _index_names(inspector, "multimodal_sessions"):
            op.drop_index(index_name, table_name="multimodal_sessions")
            inspector = sa.inspect(bind)
    for column_name in ("scope_id", "scope_type"):
        if column_name in _column_names(inspector, "multimodal_sessions"):
            op.drop_column("multimodal_sessions", column_name)
            inspector = sa.inspect(bind)
