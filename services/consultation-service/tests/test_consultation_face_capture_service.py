from __future__ import annotations

from types import SimpleNamespace

from app.services.consultation_engine import submit_consultation_face_capture


class _FakeDbSession:
    def __init__(self, session_record, turn_record) -> None:
        self._session_record = session_record
        self._turn_record = turn_record
        self.added: list[object] = []
        self.flush_count = 0

    def get(self, model, primary_key):
        model_name = getattr(model, "__name__", "")
        if model_name == "ConsultationSession" and primary_key == self._session_record.id:
            return self._session_record
        if model_name == "ConsultationTurn" and self._turn_record and primary_key == self._turn_record.id:
            return self._turn_record
        return None

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
        self.flush_count += 1


class _FakeDbContext:
    def __init__(self, db_session: _FakeDbSession) -> None:
        self._db_session = db_session

    def __enter__(self) -> _FakeDbSession:
        return self._db_session

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_submit_consultation_face_capture_caches_turn_bundle(monkeypatch) -> None:
    session_record = SimpleNamespace(
        id="consult-session-1",
        user_id="user-1",
        multimodal_session_id="mm-session-1",
        current_stage_id="stage-02-chief-complaint",
    )
    turn_record = SimpleNamespace(
        id="turn-1",
        session_id="consult-session-1",
        turn_summary_payload=None,
    )
    db_session = _FakeDbSession(session_record, turn_record)

    monkeypatch.setattr(
        "app.services.consultation_engine.get_db_session",
        lambda: _FakeDbContext(db_session),
    )
    monkeypatch.setattr(
        "app.services.consultation_engine.submit_upstream_face_capture",
        lambda **kwargs: {
            "status": 200,
            "payload": {
                "code": 0,
                "message": "ok",
                "data": {
                    "capture_id": "face-cap-001",
                    "turn_bundle": {
                        "turn_id": "turn-1",
                        "face_features": {
                            "summary_type": "turn_window",
                            "primary_label": "平静",
                            "sample_count": 8,
                            "valid_sample_count": 6,
                        },
                    },
                },
            },
        },
    )

    result = submit_consultation_face_capture(
        "consult-session-1",
        question_key="chief-complaint-001",
        turn_id="turn-1",
        sample_started_at="2026-05-21T12:00:00Z",
        sample_ended_at="2026-05-21T12:00:00Z",
        sample_index=8,
        mime_type="image/jpeg",
        filename="frame.jpg",
        file_bytes=b"jpeg-bytes",
        acting_user_id="user-1",
    )

    assert result["capture_id"] == "face-cap-001"
    assert turn_record.turn_summary_payload["turn_id"] == "turn-1"
    assert turn_record.turn_summary_payload["face_features"]["sample_count"] == 8
    assert db_session.flush_count == 1
    assert turn_record in db_session.added


def test_submit_consultation_face_capture_without_turn_id_does_not_cache_bundle(monkeypatch) -> None:
    session_record = SimpleNamespace(
        id="consult-session-2",
        user_id="user-2",
        multimodal_session_id="mm-session-2",
        current_stage_id="stage-02-chief-complaint",
    )
    db_session = _FakeDbSession(session_record, None)

    monkeypatch.setattr(
        "app.services.consultation_engine.get_db_session",
        lambda: _FakeDbContext(db_session),
    )
    monkeypatch.setattr(
        "app.services.consultation_engine.submit_upstream_face_capture",
        lambda **kwargs: {
            "status": 200,
            "payload": {
                "code": 0,
                "message": "ok",
                "data": {
                    "capture_id": "face-cap-002",
                    "turn_bundle": {
                        "turn_id": "turn-unbound",
                        "face_features": {"primary_label": "平静"},
                    },
                },
            },
        },
    )

    result = submit_consultation_face_capture(
        "consult-session-2",
        question_key="chief-complaint-001",
        turn_id=None,
        sample_started_at="2026-05-21T12:00:00Z",
        sample_ended_at="2026-05-21T12:00:00Z",
        sample_index=2,
        mime_type="image/jpeg",
        filename="frame.jpg",
        file_bytes=b"jpeg-bytes",
        acting_user_id="user-2",
    )

    assert result["capture_id"] == "face-cap-002"
    assert db_session.added == []
    assert db_session.flush_count == 1
