from __future__ import annotations

import uuid
from typing import Iterable

from fastapi import Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.security import TokenPayload, decode_jwt_token


def _resolve_admin_set(emails: Iterable[str]) -> set[str]:
    return {email.strip().lower() for email in emails if email.strip()}


async def require_admin(
    payload: TokenPayload = Depends(decode_jwt_token),
    settings: Settings = Depends(get_settings),
) -> TokenPayload:
    """
    Ensure the JWT bearer belongs to the configured admin allowlist.

    The PRD mandates all `/admin/*` endpoints require explicit admin tokens,
    so we enforce an allowlist sourced from `ADMIN_EMAILS`.
    """

    admin_emails = _resolve_admin_set(settings.admin_emails)
    if not admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is not configured",
        )

    email = (payload.email or "").strip().lower()
    if email not in admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    # Validate subject is a UUID for downstream usage; raise 401 on malformed tokens.
    try:
        uuid.UUID(payload.sub)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        ) from exc

    return payload


__all__ = ["require_admin"]
