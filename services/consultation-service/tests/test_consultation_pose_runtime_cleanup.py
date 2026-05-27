from __future__ import annotations

from app.services.consultation_engine import _finalize_turn_bundle_upstream


def test_finalize_turn_bundle_upstream_returns_turn_bundle(monkeypatch) -> None:
    observed: dict[str, str] = {}

    monkeypatch.setattr(
        "app.services.consultation_engine.finalize_upstream_multimodal_turn",
        lambda **kwargs: observed.update(kwargs)
        or {
            "status": 200,
            "payload": {
                "code": 0,
                "data": {"turn_bundle": {"turn_id": "turn-1", "visual_key_frames": []}},
            },
        },
    )

    bundle = _finalize_turn_bundle_upstream(
        multimodal_session_id="mm-session-1",
        turn_id="turn-1",
        acting_user_id="user-1",
    )

    assert observed["multimodal_session_id"] == "mm-session-1"
    assert observed["turn_id"] == "turn-1"
    assert observed["acting_user_id"] == "user-1"
    assert bundle == {"turn_id": "turn-1", "visual_key_frames": []}


def test_finalize_turn_bundle_upstream_returns_none_on_404(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.consultation_engine.finalize_upstream_multimodal_turn",
        lambda **kwargs: {"status": 404, "payload": {"code": 4044, "message": "not found"}},
    )

    bundle = _finalize_turn_bundle_upstream(
        multimodal_session_id="mm-session-2",
        turn_id="turn-2",
        acting_user_id="user-2",
    )

    assert bundle is None
