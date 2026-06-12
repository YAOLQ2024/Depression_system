from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.consultation import ConsultationServiceError
from app.services.consultation._multimodal_bridge import (
    _ensure_multimodal_session_binding,
)


def test_consultation_binding_requires_encounter_session_id(monkeypatch) -> None:
    called = False

    def fake_create_multimodal_session(**kwargs):
        nonlocal called
        called = True
        return {"status": 200, "payload": {"data": {}}}

    monkeypatch.setattr(
        "app.services.consultation._multimodal_bridge.create_upstream_multimodal_session",
        fake_create_multimodal_session,
    )

    session_record = SimpleNamespace(
        multimodal_session_id=None,
        encounter_session_id=None,
        id="consultation-session-1",
        updated_at=None,
    )

    with pytest.raises(ConsultationServiceError) as exc_info:
        _ensure_multimodal_session_binding(
            session_record,
            acting_user_id="user-1",
        )

    assert "encounter_session_id" in exc_info.value.message
    assert called is False
