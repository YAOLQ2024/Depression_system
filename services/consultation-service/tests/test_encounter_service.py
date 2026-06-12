# services/consultation-service/tests/test_encounter_service.py
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from app.services.encounter_service import list_encounters, EncounterServiceError


def _make_encounter(id, user_id="user-1", status="completed", created_at=None):
    enc = MagicMock()
    enc.id = id
    enc.user_id = user_id
    enc.status = status
    enc.current_flow_type = "consultation"
    enc.created_at = created_at or datetime(2026, 5, 20, 14, 30, tzinfo=timezone.utc)
    enc.completed_at = datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc) if status == "completed" else None
    return enc


def _make_consultation(id, encounter_id, summary="测试主诉"):
    c = MagicMock()
    c.id = id
    c.encounter_session_id = encounter_id
    c.chief_complaint_summary = summary
    c.created_at = datetime(2026, 5, 20, 14, 30, tzinfo=timezone.utc)
    return c


class TestListEncounters:
    @patch("app.services.encounter_service.get_db_session")
    def test_empty_result(self, mock_db_ctx):
        mock_session = MagicMock()
        mock_db_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        result = list_encounters("user-1")
        assert result == {"encounters": [], "next_cursor": None, "has_more": False}

    @patch("app.services.encounter_service.get_db_session")
    def test_single_page(self, mock_db_ctx):
        mock_session = MagicMock()
        mock_db_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db_ctx.return_value.__exit__ = MagicMock(return_value=False)

        enc = _make_encounter("enc-1")
        cons = _make_consultation("cons-1", "enc-1", "情绪低落")

        mock_session.execute.side_effect = [
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[enc])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[cons])))),
        ]

        result = list_encounters("user-1")
        assert len(result["encounters"]) == 1
        assert result["encounters"][0]["id"] == "enc-1"
        assert result["encounters"][0]["chief_complaint_summary"] == "情绪低落"
        assert result["has_more"] is False
        assert result["next_cursor"] is None

    @patch("app.services.encounter_service.get_db_session")
    def test_invalid_cursor_raises(self, mock_db_ctx):
        mock_session = MagicMock()
        mock_db_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute.return_value.one_or_none.return_value = None

        with pytest.raises(EncounterServiceError) as exc_info:
            list_encounters("user-1", cursor="nonexistent")
        assert exc_info.value.status_code == 400

    @patch("app.services.encounter_service.get_db_session")
    def test_has_more_with_cursor(self, mock_db_ctx):
        """When limit=1 and there are 2 encounters, has_more=True and next_cursor is set."""
        mock_session = MagicMock()
        mock_db_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db_ctx.return_value.__exit__ = MagicMock(return_value=False)

        enc1 = _make_encounter("enc-1", created_at=datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc))
        enc2 = _make_encounter("enc-2", created_at=datetime(2026, 5, 20, 14, 0, tzinfo=timezone.utc))

        # limit+1 = 2 rows returned -> has_more=True
        mock_session.execute.side_effect = [
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[enc1, enc2])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        ]

        result = list_encounters("user-1", limit=1)
        assert len(result["encounters"]) == 1
        assert result["encounters"][0]["id"] == "enc-1"
        assert result["has_more"] is True
        assert result["next_cursor"] == "enc-1"

    @patch("app.services.encounter_service.get_db_session")
    def test_multiple_encounters_with_consultations(self, mock_db_ctx):
        """Multiple encounters each with their own consultation exercises the consultation map logic."""
        mock_session = MagicMock()
        mock_db_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db_ctx.return_value.__exit__ = MagicMock(return_value=False)

        enc1 = _make_encounter("enc-1", created_at=datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc))
        enc2 = _make_encounter("enc-2", created_at=datetime(2026, 5, 20, 14, 0, tzinfo=timezone.utc))
        cons1 = _make_consultation("cons-1", "enc-1", "情绪低落")
        cons2 = _make_consultation("cons-2", "enc-2", "失眠焦虑")

        mock_session.execute.side_effect = [
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[enc1, enc2])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[cons1, cons2])))),
        ]

        result = list_encounters("user-1")
        assert len(result["encounters"]) == 2

        by_id = {e["id"]: e for e in result["encounters"]}
        assert by_id["enc-1"]["chief_complaint_summary"] == "情绪低落"
        assert by_id["enc-2"]["chief_complaint_summary"] == "失眠焦虑"
        assert by_id["enc-1"]["consultation_session_id"] == "cons-1"
        assert by_id["enc-2"]["consultation_session_id"] == "cons-2"
        assert result["has_more"] is False
