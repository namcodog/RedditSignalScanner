from __future__ import annotations

from typing import Protocol


class RedisLike(Protocol):
    async def incrby(self, key: str, amount: int = 1) -> int: ...
    async def expire(self, key: str, seconds: int) -> bool: ...
    async def ttl(self, key: str) -> int: ...


class GlobalRateLimiter:
    """Simple distributed fixed-window rate limiter using Redis.

    - Uses INCRBY with windowed EXPIRE to count requests per window.
    - When the limit is exceeded, returns remaining TTL (seconds) as backoff time.
    - Caller is responsible for sleeping when backoff > 0.
    """

    def __init__(
        self,
        redis_client: RedisLike,
        *,
        limit: int,
        window_seconds: int,
        namespace: str = "reddit_api:qpm",
        client_id: str = "default",
    ) -> None:
        self._redis = redis_client
        self._limit = int(limit)
        self._window = int(window_seconds)
        self._ns = namespace
        self._client_id = client_id

    def _key(self) -> str:
        return f"{self._ns}:{self._client_id}"

    async def acquire(self, *, cost: int = 1) -> int:
        """Attempt to acquire capacity for `cost` requests.

        Returns:
            0 when allowed immediately, or number of seconds to wait otherwise.
        """
        key = self._key()
        new_total = await self._redis.incrby(key, cost)
        # set window expiry when first seen in the current window
        if new_total == cost:
            await self._redis.expire(key, self._window)
        if new_total > self._limit:
            ttl = await self._redis.ttl(key)
            return max(1, int(ttl) if isinstance(ttl, int) else 1)
        return 0

