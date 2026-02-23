from __future__ import annotations

import os
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError

GOLD_DATABASE_NAME = "reddit_signal_scanner"


def _normalize_environment(value: str) -> str:
    return value.strip().lower()


def _allow_gold_db() -> bool:
    return os.getenv("ALLOW_GOLD_DB", "").strip().lower() in {"1", "true", "yes", "on"}


def _is_production_env(environment: str) -> bool:
    return environment in {"production", "prod", "staging"}


def _extract_database_name(database_url: str) -> str:
    try:
        return make_url(database_url).database or ""
    except ArgumentError:
        return ""


def validate_database_target(
    database_url: str,
    *,
    environment: str | None = None,
    allow_gold_db: bool | None = None,
) -> None:
    """Block accidental writes to the gold DB in non-prod environments."""
    env_value = _normalize_environment(
        environment or os.getenv("APP_ENV", "development")
    )
    if _is_production_env(env_value):
        return

    allow_gold = allow_gold_db if allow_gold_db is not None else _allow_gold_db()
    db_name = _extract_database_name(database_url)
    if not db_name:
        return

    if db_name == GOLD_DATABASE_NAME and not allow_gold:
        raise RuntimeError(
            "Gold database access is blocked in non-prod environments. "
            "Set ALLOW_GOLD_DB=1 to override."
        )
