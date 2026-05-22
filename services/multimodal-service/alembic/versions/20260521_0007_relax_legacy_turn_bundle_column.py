"""Relax legacy turn bundle column to allow Step 6 legacy-write shutdown.

Revision ID: 20260521_0007
Revises: 20260521_0006
Create Date: 2026-05-21 10:25:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260521_0007"
down_revision = "20260521_0006"
branch_labels = None
depends_on = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_map(
    inspector: sa.Inspector,
    table_name: str,
) -> dict[str, dict[str, object]]:
    return {
        column["name"]: column
        for column in inspector.get_columns(table_name)
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)
    if "multimodal_turn_bundles" not in existing_tables:
        return

    bundle_columns = _column_map(inspector, "multimodal_turn_bundles")
    if "consultation_turn_id" in bundle_columns:
        op.alter_column(
            "multimodal_turn_bundles",
            "consultation_turn_id",
            existing_type=bundle_columns["consultation_turn_id"]["type"],
            nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)
    if "multimodal_turn_bundles" not in existing_tables:
        return

    bundle_columns = _column_map(inspector, "multimodal_turn_bundles")
    if "consultation_turn_id" in bundle_columns:
        op.alter_column(
            "multimodal_turn_bundles",
            "consultation_turn_id",
            existing_type=bundle_columns["consultation_turn_id"]["type"],
            nullable=False,
        )
