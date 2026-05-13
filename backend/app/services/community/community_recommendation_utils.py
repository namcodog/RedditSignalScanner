from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from app.services.community.community_recommendation_models import JsonValue


def normalize_text(value: object) -> str:
    return str(value or "").strip().lower()


def tokenize(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def parse_activity_at(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def is_within_15d(value: str | None, *, now: datetime | None = None) -> bool:
    parsed = parse_activity_at(value)
    if parsed is None:
        return False
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return parsed >= current - timedelta(days=15)


def latest_activity(left: str | None, right: str | None) -> str | None:
    left_at = parse_activity_at(left)
    right_at = parse_activity_at(right)
    if left_at is None:
        return right
    if right_at is None:
        return left
    return right if right_at > left_at else left


def flatten_json_values(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        out: list[str] = []
        for nested in value.values():
            out.extend(flatten_json_values(nested))
        return tuple(out)
    if isinstance(value, list):
        out = []
        for nested in value:
            out.extend(flatten_json_values(nested))
        return tuple(out)
    return (str(value),)


def to_json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, tuple | list):
        return [to_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_json_value(item) for key, item in value.items()}
    return str(value)


def dedupe(items: tuple[str, ...] | list[str], *, limit: int = 5) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= limit:
            break
    return tuple(out)
