from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Mapping, cast

import redis

from app.core.config import Settings
from app.middleware.route_metrics import DEFAULT_ROUTE_METRICS_KEY_PREFIX


def as_float(value: object, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def as_int(value: object, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def get_metrics_redis(
    settings: Settings,
    *,
    metrics_redis_url: str | None,
) -> redis.Redis:  # type: ignore[type-arg]
    target_url = metrics_redis_url or settings.reddit_cache_redis_url
    return redis.Redis.from_url(target_url)


def send_alert(
    *,
    task_logger: logging.Logger,
    std_logger: logging.Logger,
    level: str,
    message: str,
) -> None:
    formatted = f"[{level.upper()}] {message}"
    task_logger.warning(formatted)
    std_logger.warning(formatted)


def load_e2e_metrics(
    *,
    test_metrics_path: Path,
    std_logger: logging.Logger,
) -> dict[str, Any] | None:
    if not test_metrics_path.exists():
        return None
    try:
        payload = json.loads(test_metrics_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return None
        return payload
    except json.JSONDecodeError:
        std_logger.warning("无法解析测试指标文件: %s", test_metrics_path)
        return None


def update_dashboard(
    settings: Settings,
    values: dict[str, Any],
    *,
    get_metrics_redis: Callable[[Settings], redis.Redis],  # type: ignore[type-arg]
    performance_dashboard_key: str,
    utc_now: Callable[[], Any],
) -> None:
    client = get_metrics_redis(settings)
    enriched: dict[str, str] = {
        key: json.dumps(value, ensure_ascii=False)
        if isinstance(value, (dict, list))
        else str(value)
        for key, value in values.items()
    }
    client.hset(
        performance_dashboard_key,
        mapping=cast(Mapping[str | bytes, bytes | float | int | str], enriched),
    )
    client.hset(performance_dashboard_key, "updated_at", utc_now().isoformat())


def route_metrics_bucket(*, utc_now: Callable[[], Any]) -> int:
    return int(utc_now().timestamp() // 60)


def decode_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="ignore")
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return 0
    return 0


def load_route_call_metrics(
    client: redis.Redis,  # type: ignore[type-arg]
    *,
    bucket: int,
    top_n: int,
    route_metrics_key_prefix: str = DEFAULT_ROUTE_METRICS_KEY_PREFIX,
) -> tuple[int, int, list[dict[str, Any]]]:
    key = f"{route_metrics_key_prefix}:{bucket}"
    raw = client.hgetall(key) or {}
    decoded: dict[str, int] = {}
    for key_value, value in raw.items():
        field = (
            key_value.decode("utf-8", errors="ignore")
            if isinstance(key_value, (bytes, bytearray))
            else str(key_value)
        )
        decoded[field] = decode_int(value)

    golden_total = decoded.get("golden|_total", 0)
    legacy_total = decoded.get("legacy|_total", 0)

    legacy_rows: list[dict[str, Any]] = []
    for field, count in decoded.items():
        if not field.startswith("legacy|") or field == "legacy|_total":
            continue
        parts = field.split("|", 2)
        if len(parts) != 3:
            continue
        _, method, path = parts
        if method == "_total":
            continue
        legacy_rows.append({"route": f"{method} {path}", "count": int(count)})

    legacy_rows.sort(key=lambda item: int(item.get("count", 0)), reverse=True)
    return golden_total, legacy_total, legacy_rows[: max(0, int(top_n))]


__all__ = [
    "as_float",
    "as_int",
    "decode_int",
    "get_metrics_redis",
    "load_e2e_metrics",
    "load_route_call_metrics",
    "route_metrics_bucket",
    "send_alert",
    "update_dashboard",
]
