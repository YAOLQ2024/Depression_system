from __future__ import annotations

from pydantic import BaseModel, Field


class CreateMultimodalSessionRequest(BaseModel):
    consultation_session_id: str = Field(min_length=1)
    workflow_id: str | None = None
