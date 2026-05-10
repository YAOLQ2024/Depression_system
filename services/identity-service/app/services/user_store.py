from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.config import get_settings
from app.database import get_db_session
from app.models import SessionToken, User

ROLE_CHOICES = ["admin", "researcher", "participant"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_account(account: str) -> str:
    normalized = account.strip()
    return normalized.lower() if "@" in normalized else normalized


def _hash_password(password: str, salt: str) -> str:
    payload = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return payload.hex()


def _verify_password(password: str, salt: str, expected_hash: str) -> bool:
    candidate = _hash_password(password, salt)
    return hmac.compare_digest(candidate, expected_hash)


def _public_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "profile_status": user.profile_status,
        "profile": {
            "age": user.age,
            "height_cm": user.height_cm,
            "weight_kg": user.weight_kg,
            "marital_status": user.marital_status,
            "parents_marital_status": user.parents_marital_status,
            "parents_occupation": user.parents_occupation,
            "prior_psychiatric_visit": user.prior_psychiatric_visit,
            "family_history": user.family_history,
        },
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


def ensure_seed_users() -> None:
    defaults = [
        ("admin@mcs.local", "Admin123!", "系统管理员", "admin"),
        ("researcher@mcs.local", "Research123!", "研究员示例账号", "researcher"),
        ("participant@mcs.local", "Participant123!", "受试者示例账号", "participant"),
    ]
    with get_db_session() as session:
        for email, password, full_name, role in defaults:
            existing = session.scalar(select(User).where(User.email == email))
            if existing:
                continue
            salt = secrets.token_hex(16)
            now = _now()
            session.add(
                User(
                    id=str(uuid.uuid4()),
                    email=email,
                    password_hash=_hash_password(password, salt),
                    password_salt=salt,
                    full_name=full_name,
                    role=role,
                    profile_status="draft",
                    created_at=now,
                    updated_at=now,
                )
            )


def create_user(account: str, password: str, full_name: str, role: str = "participant") -> dict:
    normalized_account = normalize_account(account)

    with get_db_session() as session:
        existing = session.scalar(select(User).where(User.email == normalized_account))
        if existing:
            raise ValueError("account already registered")

        salt = secrets.token_hex(16)
        now = _now()
        user = User(
            id=str(uuid.uuid4()),
            email=normalized_account,
            password_hash=_hash_password(password, salt),
            password_salt=salt,
            full_name=full_name.strip(),
            role=role,
            profile_status="draft",
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.flush()
        session.refresh(user)
        return _public_user(user)


def _create_session(user_id: str) -> str:
    session_token = secrets.token_urlsafe(32)
    settings = get_settings()
    now = _now()
    expires_at = now + timedelta(hours=settings["session_ttl_hours"])
    with get_db_session() as session:
        session.add(
            SessionToken(
                token=session_token,
                user_id=user_id,
                created_at=now,
                expires_at=expires_at,
            )
        )
    return session_token


def authenticate_user(account: str, password: str) -> dict | None:
    normalized_account = normalize_account(account)

    with get_db_session() as session:
        user = session.scalar(select(User).where(User.email == normalized_account))
        if not user:
            return None
        if not _verify_password(password, user.password_salt, user.password_hash):
            return None
        token = _create_session(user.id)
        return {"session_token": token, "user": _public_user(user)}


def get_user_by_session_token(session_token: str) -> dict | None:
    with get_db_session() as session:
        session_record = session.scalar(select(SessionToken).where(SessionToken.token == session_token))
        if not session_record:
            return None
        if session_record.expires_at < _now():
            session.delete(session_record)
            session.flush()
            return None
        user = session.get(User, session_record.user_id)
        if not user:
            return None
        return _public_user(user)


def revoke_session(session_token: str) -> None:
    with get_db_session() as session:
        session_record = session.get(SessionToken, session_token)
        if session_record:
            session.delete(session_record)


def update_profile(user_id: str, payload: dict) -> dict:
    allowed_fields = {
        "full_name",
        "age",
        "height_cm",
        "weight_kg",
        "marital_status",
        "parents_marital_status",
        "parents_occupation",
        "prior_psychiatric_visit",
        "family_history",
    }
    updates = {key: value for key, value in payload.items() if key in allowed_fields}

    with get_db_session() as session:
        user = session.get(User, user_id)
        if not user:
            raise ValueError("user not found")

        if not updates:
            return _public_user(user)

        for key, value in updates.items():
            setattr(user, key, value)

        user.profile_status = "completed" if any(value not in (None, "") for value in updates.values()) else "draft"
        user.updated_at = _now()
        session.flush()
        session.refresh(user)
        return _public_user(user)
