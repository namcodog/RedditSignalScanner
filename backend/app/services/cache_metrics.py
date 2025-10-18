from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol, cast

import redis

DEFAULT_BUCKET_TTL_SECONDS = 24 * 60 * 60  # keep per-minute buckets for 24h


class RedisLikeMetrics(Protocol):
    def incrby(self, name: str, amount: int = 1) -> int:
        ...

    def expire(self, name: str, time: int) -> bool | int | None:
        ...

    def get(self, name: str) -> bytes | str | None:
        ...


class CacheMetrics:
    """
    Application-level cache hit/miss metrics with minute buckets stored in Redis.

    - record_hit()/record_miss() will increment per-minute counters and set TTL
    - calculate_hit_rate() aggregates buckets over a time-window (default 60 min)
    """

    def __init__(
        self,
        redis_client: RedisLikeMetrics | None = None,
        *,
        namespace: str = "metrics:cache",
        redis_url: str | None = None,
        bucket_ttl_seconds: int = DEFAULT_BUCKET_TTL_SECONDS,
    ) -> None:
        if redis_client is not None:
            self._redis = redis_client
        else:
            target_url = redis_url or "redis://localhost:6379/5"
            self._redis = cast(RedisLikeMetrics, redis.Redis.from_url(target_url))
        self._ns = namespace.strip(":")
        self._bucket_ttl = max(60, bucket_ttl_seconds)

    # -------------------- Public API --------------------
    async def record_hit(self, *, now: datetime | None = None) -> None:
        self._incr_bucket("hit", 1, now)

    async def record_miss(self, *, now: datetime | None = None) -> None:
        self._incr_bucket("miss", 1, now)

    async def calculate_hit_rate(
        self, *, window_minutes: int = 60, now: datetime | None = None
    ) -> float:
        hits, misses = self._get_counts(window_minutes=window_minutes, now=now)
        total = hits + misses
        if total <= 0:
            return 0.0
        return hits / total

    async def get_counts(
        self, *, window_minutes: int = 60, now: datetime | None = None
    ) -> tuple[int, int]:
        return self._get_counts(window_minutes=window_minutes, now=now)

    # -------------------- Internal helpers --------------------
    def _minute_bucket(self, dt: datetime | None) -> str:
        d = dt or datetime.now(timezone.utc)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        # bucket per minute: YYYYMMDDHHMM
        return d.strftime("%Y%m%d%H%M")

    def _key(self, kind: str, bucket: str) -> str:
        return f"{self._ns}:{kind}:{bucket}"

    def _incr_bucket(self, kind: str, amount: int, now: datetime | None) -> None:
        bucket = self._minute_bucket(now)
        key = self._key(kind, bucket)
        # incr counter and (re)set TTL so buckets naturally expire
        self._redis.incrby(key, amount)
        # Best-effort TTL; redis returns bool/int, we ignore the return value
        self._redis.expire(key, self._bucket_ttl)

    def _get_counts(
        self, *, window_minutes: int, now: datetime | None
    ) -> tuple[int, int]:
        if window_minutes <= 0:
            return (0, 0)
        end = now or datetime.now(timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        start = end - timedelta(minutes=window_minutes - 1)

        hits = 0
        misses = 0
        cur = start
        while cur <= end:
            bucket = self._minute_bucket(cur)
            h_raw = self._redis.get(self._key("hit", bucket))
            m_raw = self._redis.get(self._key("miss", bucket))
            if h_raw is not None:
                hits += _to_int(h_raw)
            if m_raw is not None:
                misses += _to_int(m_raw)
            cur = cur + timedelta(minutes=1)
        return hits, misses


def _to_int(v: bytes | str | None) -> int:
    if v is None:
        return 0
    if isinstance(v, bytes):
        try:
            return int(v.decode("utf-8"))
        except Exception:
            return 0
    try:
        return int(v)
    except Exception:
        return 0


__all__ = ["CacheMetrics", "RedisLikeMetrics"]
