"""harden multimodal session scope constraints

Revision ID: 20260529_0012
Revises: 20260529_0011
Create Date: 2026-05-29 22:30:00

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260529_0012"
down_revision = "20260529_0011"
branch_labels = None
depends_on = None


def _check_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {
        constraint["name"]
        for constraint in inspector.get_check_constraints(table_name)
        if constraint.get("name")
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    op.execute(
        sa.text(
            """
            UPDATE multimodal_sessions
            SET encounter_session_id = NULLIF(encounter_session_id, ''),
                scope_type = COALESCE(
                    NULLIF(scope_type, ''),
                    CASE
                        WHEN NULLIF(encounter_session_id, '') IS NOT NULL THEN 'encounter'
                        ELSE 'flow'
                    END
                ),
                scope_id = CASE
                    WHEN COALESCE(
                        NULLIF(scope_type, ''),
                        CASE
                            WHEN NULLIF(encounter_session_id, '') IS NOT NULL THEN 'encounter'
                            ELSE 'flow'
                        END
                    ) = 'encounter'
                    THEN COALESCE(NULLIF(encounter_session_id, ''), NULLIF(scope_id, ''))
                    ELSE COALESCE(NULLIF(scope_id, ''), NULLIF(flow_run_id, ''))
                END
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE multimodal_sessions
            SET encounter_session_id = scope_id
            WHERE scope_type = 'encounter'
              AND scope_id IS NOT NULL
              AND (
                encounter_session_id IS NULL
                OR encounter_session_id <> scope_id
              )
            """
        )
    )

    op.alter_column(
        "multimodal_sessions",
        "scope_type",
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.alter_column(
        "multimodal_sessions",
        "scope_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )

    if (
        "ck_multimodal_sessions_encounter_scope_consistency"
        not in _check_names(inspector, "multimodal_sessions")
    ):
        op.create_check_constraint(
            "ck_multimodal_sessions_encounter_scope_consistency",
            "multimodal_sessions",
            "(scope_type <> 'encounter') OR "
            "(encounter_session_id IS NOT NULL AND encounter_session_id = scope_id)",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if (
        "ck_multimodal_sessions_encounter_scope_consistency"
        in _check_names(inspector, "multimodal_sessions")
    ):
        op.drop_constraint(
            "ck_multimodal_sessions_encounter_scope_consistency",
            "multimodal_sessions",
            type_="check",
        )

    op.alter_column(
        "multimodal_sessions",
        "scope_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )
    op.alter_column(
        "multimodal_sessions",
        "scope_type",
        existing_type=sa.String(length=64),
        nullable=True,
    )
