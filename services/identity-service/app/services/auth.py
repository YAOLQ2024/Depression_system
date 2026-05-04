from __future__ import annotations


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    if authorization.startswith("Bearer "):
        return authorization[7:].strip() or None
    return authorization.strip() or None
