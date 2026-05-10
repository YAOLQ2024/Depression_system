from __future__ import annotations

import re

from pydantic import AliasChoices, BaseModel, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^1\d{10}$")


def _normalize_account(value: str) -> str:
    normalized = value.strip()
    return normalized.lower() if "@" in normalized else normalized


def _validate_account(value: str) -> str:
    if "@" in value:
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("account must be a valid email address")
        return value

    if not PHONE_PATTERN.fullmatch(value):
        raise ValueError("account must be a valid 11-digit mobile phone number")

    return value


class RegisterRequest(BaseModel):
    account: str = Field(min_length=3, validation_alias=AliasChoices("account", "email"))
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=1)

    @field_validator("account", mode="before")
    @classmethod
    def normalize_account(cls, value: str) -> str:
        return _normalize_account(value)

    @field_validator("account")
    @classmethod
    def validate_account(cls, value: str) -> str:
        return _validate_account(value)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("full_name is required")
        return normalized


class LoginRequest(BaseModel):
    account: str = Field(min_length=3, validation_alias=AliasChoices("account", "email"))
    password: str = Field(min_length=6)

    @field_validator("account", mode="before")
    @classmethod
    def normalize_account(cls, value: str) -> str:
        return _normalize_account(value)

    @field_validator("account")
    @classmethod
    def validate_account(cls, value: str) -> str:
        return _validate_account(value)
