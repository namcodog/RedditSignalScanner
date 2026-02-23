from __future__ import annotations

import json
import pytest

from app.services.hotpost.queue import HotpostQueueTracker


class _FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.counters: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def decr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) - 1
        return self.counters[key]

    async def setex(self, key: str, _seconds: int, value: str) -> bool:
        self.data[key] = value
        return True

    async def set(self, key: str, value: int) -> bool:
        self.counters[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self.data.get(key)


@pytest.mark.asyncio
async def test_queue_tracker_waiting_and_processing() -> None:
    redis = _FakeRedis()
    tracker = HotpostQueueTracker(redis, "qid", ttl_seconds=60)

    await tracker.mark_waiting(estimated_wait_seconds=12)
    payload = json.loads(await redis.get("hotpost:queue:qid") or "{}")
    assert payload["status"] == "waiting"
    assert payload["position"] == 1

    await tracker.mark_processing()
    payload = json.loads(await redis.get("hotpost:queue:qid") or "{}")
    assert payload["status"] == "processing"

    await tracker.mark_completed()
    payload = json.loads(await redis.get("hotpost:queue:qid") or "{}")
    assert payload["status"] == "completed"
