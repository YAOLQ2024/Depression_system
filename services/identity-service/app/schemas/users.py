from __future__ import annotations

from pydantic import BaseModel, Field


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    gender: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    height_cm: float | None = Field(default=None, ge=0)
    weight_kg: float | None = Field(default=None, ge=0)
    marital_status: str | None = None
    parents_marital_status: str | None = None
    parents_occupation: str | None = None
    prior_psychiatric_visit: str | None = None
