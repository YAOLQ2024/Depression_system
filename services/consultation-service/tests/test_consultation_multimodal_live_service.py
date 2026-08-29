from __future__ import annotations

from types import SimpleNamespace

from app.services.consultation_engine import get_consultation_multimodal_live


class _FakeDbSession:
    def __init__(self, session_record) -> None:
        self._session_record = session_record
        self.flush_count = 0

    def get(self, model, primary_key):
        model_name = getattr(model, "__name__", "")
        if model_name == "ConsultationSession" and primary_key == self._session_record.id:
            return self._session_record
        return None

    def flush(self) -> None:
        self.flush_count += 1


class _FakeDbContext:
    def __init__(self, db_session: _FakeDbSession) -> None:
        self._db_session = db_session

    def __enter__(self) -> _FakeDbSession:
        return self._db_session

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_get_consultation_multimodal_live_does_not_flush_snapshot_reads(
    monkeypatch,
) -> None:
    session_record = SimpleNamespace(
        id="consult-session-1",
        user_id="user-1",
        multimodal_session_id="mm-session-1",
        status="running",
    )
    db_session = _FakeDbSession(session_record)
    live_payload = {
        "session_id": "mm-session-1",
        "updated_at": "2026-05-27T12:00:00Z",
        "speech": {"status": "ready"},
        "text": {"status": "ready"},
        "face": {"status": "ready"},
        "pose": {"status": "ready"},
    }

    monkeypatch.setattr(
        "app.services.consultation_engine.get_db_session",
        lambda: _FakeDbContext(db_session),
    )
    monkeypatch.setattr(
        "app.services.consultation_engine._refresh_multimodal_live_snapshot",
        lambda session_record, *, acting_user_id: live_payload,
    )

    result = get_consultation_multimodal_live(
        "consult-session-1",
        acting_user_id="user-1",
    )

    assert result == live_payload
    assert db_session.flush_count == 0


def test_get_consultation_multimodal_live_does_not_restart_active_eeg_turn(
    monkeypatch,
) -> None:
    session_record = SimpleNamespace(
        id="consult-session-1",
        user_id="user-1",
        multimodal_session_id="mm-session-1",
        status="waiting_user_input",
    )
    db_session = _FakeDbSession(session_record)
    live_payload = {"session_id": "mm-session-1", "eeg_waves": {"samples": []}}

    monkeypatch.setattr(
        "app.services.consultation_engine.get_db_session",
        lambda: _FakeDbContext(db_session),
    )
    monkeypatch.setattr(
        "app.services.consultation_engine._ensure_multimodal_session_binding",
        lambda session_record, *, acting_user_id: "mm-session-1",
    )
    monkeypatch.setattr(
        "app.services.consultation_engine._refresh_multimodal_live_snapshot",
        lambda session_record, *, acting_user_id: live_payload,
    )

    def fail_if_eeg_turn_restarts(**_) -> None:
        raise AssertionError("EEG turn must not restart on a live read")

    monkeypatch.setattr(
        "app.services.consultation_engine._start_eeg_turn_best_effort",
        fail_if_eeg_turn_restarts,
    )

    result = get_consultation_multimodal_live(
        "consult-session-1",
        acting_user_id="user-1",
    )

    assert result == live_payload
