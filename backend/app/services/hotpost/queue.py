from __future__ import annotations

import json
import time
from typing import Protocol


class RedisQueueClient(Protocol):
    async def incr(self, key: str) -> int: ...
    async def decr(self, key: str) -> int: ...
    async def setex(self, key: str, seconds: int, value: str) -> bool: ...
    async def set(self, key: str, value: int) -> bool: ...


class HotpostQueueTracker:
    def __init__(self, redis: RedisQueueClient, query_id: str, *, ttl_seconds: int = 600) -> None:
        self._redis = redis
        self._query_id = query_id
        self._key = f"hotpost:queue:{query_id}"
        self._pending_key = "hotpost:queue:pending"
        self._ttl = ttl_seconds
        self._queued = False
        self._position: int | None = None

    async def _set_status(
        self,
        *,
        status: str,
        position: int | None = None,
        estimated_wait_seconds: int | None = None,
        message: str | None = None,
    ) -> None:
        payload = {
            "query_id": self._query_id,
            "status": status,
            "position": position,
            "estimated_wait_seconds": estimated_wait_seconds,
            "message": message,
            "updated_at": int(time.time()),
        }
        await self._redis.setex(self._key, self._ttl, json.dumps(payload, ensure_ascii=False))

    async def _release_position(self) -> None:
        value = await self._redis.decr(self._pending_key)
        if value < 0:
            await self._redis.set(self._pending_key, 0)

    async def mark_processing(self) -> None:
        if self._queued:
            await self._release_position()
            self._queued = False
        await self._set_status(status="processing", position=self._position, estimated_wait_seconds=0)

    async def mark_waiting(self, *, estimated_wait_seconds: int) -> None:
        if not self._queued:
            self._position = await self._redis.incr(self._pending_key)
            self._queued = True
        await self._set_status(
            status="waiting",
            position=self._position,
            estimated_wait_seconds=estimated_wait_seconds,
        )

    async def mark_completed(self) -> None:
        if self._queued:
            await self._release_position()
            self._queued = False
        await self._set_status(status="completed", position=self._position, estimated_wait_seconds=0)

    async def mark_failed(self, message: str | None = None) -> None:
        if self._queued:
            await self._release_position()
            self._queued = False
        await self._set_status(status="failed", position=self._position, message=message)


__all__ = ["HotpostQueueTracker"]
