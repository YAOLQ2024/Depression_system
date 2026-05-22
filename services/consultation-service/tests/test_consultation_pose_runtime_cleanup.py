from __future__ import annotations

from app.services.consultation_engine import _clear_pose_turn_runtime_best_effort


def test_clear_pose_turn_runtime_best_effort_forwards_when_ids_present(monkeypatch) -> None:
    observed: dict[str, str] = {}

    monkeypatch.setattr(
        "app.services.consultation_engine.clear_upstream_pose_turn_runtime",
        lambda **kwargs: observed.update(kwargs) or {"status": 200, "payload": {"code": 0, "data": {}}},
    )

    _clear_pose_turn_runtime_best_effort(
        multimodal_session_id="mm-session-1",
        turn_id="turn-1",
        acting_user_id="user-1",
    )

    assert observed["multimodal_session_id"] == "mm-session-1"
    assert observed["turn_id"] == "turn-1"
    assert observed["acting_user_id"] == "user-1"


def test_clear_pose_turn_runtime_best_effort_swallows_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.consultation_engine.clear_upstream_pose_turn_runtime",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("network-error")),
    )

    _clear_pose_turn_runtime_best_effort(
        multimodal_session_id="mm-session-2",
        turn_id="turn-2",
        acting_user_id="user-2",
    )
