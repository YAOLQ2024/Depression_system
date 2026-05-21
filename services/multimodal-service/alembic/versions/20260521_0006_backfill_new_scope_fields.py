"""backfill new scope fields in multimodal tables

Revision ID: 20260521_0006
Revises: 20260520_0005
Create Date: 2026-05-21 10:20:00

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260521_0006"
down_revision = "20260520_0005"
branch_labels = None
depends_on = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = _table_names(inspector)

    if "multimodal_sessions" in existing_tables:
        op.execute(
            sa.text(
                """
                UPDATE multimodal_sessions
                SET
                    flow_type = COALESCE(flow_type, 'consultation'),
                    flow_run_id = COALESCE(flow_run_id, owner_session_id),
                    live_state_payload = COALESCE(
                        live_state_payload,
                        latest_live_payload
                    )
                """
            )
        )

    if "multimodal_captures" in existing_tables:
        op.execute(
            sa.text(
                """
                UPDATE multimodal_captures AS capture_row
                SET
                    turn_id = COALESCE(
                        capture_row.turn_id,
                        capture_row.consultation_turn_id
                    ),
                    flow_run_id = COALESCE(
                        capture_row.flow_run_id,
                        NULLIF(capture_row.capture_payload ->> 'flow_run_id', ''),
                        NULLIF(
                            capture_row.capture_payload ->> 'consultation_session_id',
                            ''
                        ),
                        session_row.flow_run_id
                    ),
                    question_key = COALESCE(
                        capture_row.question_key,
                        NULLIF(capture_row.capture_payload ->> 'question_key', '')
                    ),
                    sample_index = COALESCE(
                        capture_row.sample_index,
                        NULLIF(capture_row.capture_payload ->> 'sample_index', '')::integer,
                        NULLIF(capture_row.capture_payload ->> 'frame_index', '')::integer
                    ),
                    sample_started_at = COALESCE(
                        capture_row.sample_started_at,
                        NULLIF(
                            capture_row.capture_payload ->> 'sample_started_at',
                            ''
                        )::timestamptz,
                        NULLIF(
                            capture_row.capture_payload ->> 'capture_started_at',
                            ''
                        )::timestamptz
                    ),
                    sample_ended_at = COALESCE(
                        capture_row.sample_ended_at,
                        NULLIF(
                            capture_row.capture_payload ->> 'sample_ended_at',
                            ''
                        )::timestamptz,
                        NULLIF(
                            capture_row.capture_payload ->> 'capture_ended_at',
                            ''
                        )::timestamptz
                    )
                FROM multimodal_sessions AS session_row
                WHERE session_row.id = capture_row.session_id
                """
            )
        )

    if "multimodal_inference_results" in existing_tables:
        op.execute(
            sa.text(
                """
                UPDATE multimodal_inference_results AS result_row
                SET
                    turn_id = COALESCE(
                        result_row.turn_id,
                        result_row.consultation_turn_id
                    ),
                    flow_run_id = COALESCE(
                        result_row.flow_run_id,
                        NULLIF(
                            result_row.inference_payload ->> 'flow_run_id',
                            ''
                        ),
                        NULLIF(
                            result_row.inference_payload ->> 'consultation_session_id',
                            ''
                        ),
                        session_row.flow_run_id
                    ),
                    question_key = COALESCE(
                        result_row.question_key,
                        NULLIF(
                            result_row.inference_payload ->> 'question_key',
                            ''
                        )
                    )
                FROM multimodal_sessions AS session_row
                WHERE session_row.id = result_row.session_id
                """
            )
        )

    if "multimodal_turn_bundles" in existing_tables:
        op.execute(
            sa.text(
                """
                UPDATE multimodal_turn_bundles AS bundle_row
                SET
                    turn_id = COALESCE(
                        bundle_row.turn_id,
                        bundle_row.consultation_turn_id
                    ),
                    flow_run_id = COALESCE(
                        bundle_row.flow_run_id,
                        NULLIF(bundle_row.bundle_payload ->> 'flow_run_id', ''),
                        session_row.flow_run_id
                    ),
                    stage_id = COALESCE(
                        bundle_row.stage_id,
                        NULLIF(bundle_row.bundle_payload ->> 'stage_id', '')
                    ),
                    question_key = COALESCE(
                        bundle_row.question_key,
                        NULLIF(bundle_row.bundle_payload ->> 'question_key', '')
                    )
                FROM multimodal_sessions AS session_row
                WHERE session_row.id = bundle_row.session_id
                """
            )
        )


def downgrade() -> None:
    pass
