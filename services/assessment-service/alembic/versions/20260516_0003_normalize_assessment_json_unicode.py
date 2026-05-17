"""normalize unicode escaping in assessment json columns

Revision ID: 20260516_0003
Revises: 20260504_0002
Create Date: 2026-05-16 15:40:00

"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260516_0003"
down_revision = "20260504_0002"
branch_labels = None
depends_on = None


def _normalize_json_columns(
    table_name: str, key_column: str, columns: tuple[str, ...]
) -> None:
    bind = op.get_bind()
    select_list = ", ".join([key_column, *columns])
    rows = (
        bind.execute(sa.text(f"SELECT {select_list} FROM {table_name}"))
        .mappings()
        .all()
    )

    for row in rows:
        assignments: list[str] = []
        params: dict[str, object] = {key_column: row[key_column]}

        for column in columns:
            value = row[column]
            if value is None:
                continue
            params[column] = json.dumps(
                value, ensure_ascii=False, separators=(",", ":")
            )
            assignments.append(f"{column} = CAST(:{column} AS json)")

        if not assignments:
            continue

        bind.execute(
            sa.text(
                f"UPDATE {table_name} "
                f"SET {', '.join(assignments)} "
                f"WHERE {key_column} = :{key_column}"
            ),
            params,
        )


def upgrade() -> None:
    _normalize_json_columns(
        "assessment_sessions",
        "id",
        (
            "required_scales",
            "selected_scales",
            "scale_handoff_payload",
            "capture_context",
            "aggregate_payload",
        ),
    )
    _normalize_json_columns(
        "assessment_results",
        "id",
        ("risk_flags",),
    )


def downgrade() -> None:
    pass
