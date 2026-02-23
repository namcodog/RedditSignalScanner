from __future__ import annotations

from contextvars import ContextVar
from uuid import UUID

_CURRENT_USER_ID: ContextVar[str | None] = ContextVar("current_user_id", default=None)

DEFAULT_RLS_USER_ID = UUID("00000000-0000-0000-0000-000000000000")


def set_current_user_id(user_id: UUID | str) -> None:
    value = str(user_id).strip()
    _CURRENT_USER_ID.set(value if value else None)


def unset_current_user_id() -> None:
    _CURRENT_USER_ID.set(None)


def get_current_user_id() -> str | None:
    value = _CURRENT_USER_ID.get()
    if not value:
        return None
    value = value.strip()
    return value or None


def resolve_current_user_id_for_rls() -> str:
    return get_current_user_id() or str(DEFAULT_RLS_USER_ID)

