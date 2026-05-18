from __future__ import annotations

from pydantic import BaseModel, Field


class MultimodalStageContext(BaseModel):
    stage_id: str = Field(min_length=1)
    stage_label: str = Field(min_length=1)
    stage_order: int = Field(ge=1)


class CreateMultimodalSessionRequest(BaseModel):
    owner_service: str = Field(min_length=1)
    owner_session_id: str = Field(min_length=1)
    user_id: str | None = None
    stage_context: MultimodalStageContext
