"""backfill new scope fields in consultation tables

Revision ID: 20260521_0013
Revises: 20260520_0012
Create Date: 2026-05-21 10:20:00

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260521_0013"
down_revision = "20260520_0012"
branch_labels = None
depends_on = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)
    if "consultation_turns" not in existing_tables:
        return

    op.execute(
        sa.text(
            """
            UPDATE consultation_turns AS turn_row
            SET
                encounter_session_id = COALESCE(
                    turn_row.encounter_session_id,
                    session_row.encounter_session_id
                ),
                consultation_flow_run_id = COALESCE(
                    turn_row.consultation_flow_run_id,
                    turn_row.session_id
                ),
                question_key = COALESCE(turn_row.question_key, turn_row.prompt_key),
                question_order = COALESCE(turn_row.question_order, turn_row.prompt_order),
                question_video_asset_id = COALESCE(
                    turn_row.question_video_asset_id,
                    turn_row.prompt_video_asset_id
                ),
                question_video_uri = COALESCE(
                    turn_row.question_video_uri,
                    turn_row.prompt_video_uri
                ),
                question_text = COALESCE(
                    turn_row.question_text,
                    turn_row.prompt_question_text
                ),
                question_subtitle_text = COALESCE(
                    turn_row.question_subtitle_text,
                    turn_row.prompt_subtitle_text
                ),
                turn_window_started_at = COALESCE(
                    turn_row.turn_window_started_at,
                    turn_row.response_started_at
                ),
                turn_window_completed_at = COALESCE(
                    turn_row.turn_window_completed_at,
                    turn_row.response_completed_at
                ),
                turn_summary_payload = COALESCE(
                    turn_row.turn_summary_payload,
                    turn_row.multimodal_bundle_payload
                )
            FROM consultation_sessions AS session_row
            WHERE session_row.id = turn_row.session_id
            """
        )
    )


def downgrade() -> None:
    pass
