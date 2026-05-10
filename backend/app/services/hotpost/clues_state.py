from __future__ import annotations

import time

from redis.asyncio import Redis


def _events_key(day: str) -> str:
    return f"hotpost:cards:events:{day}"


def _card_events_key(day: str, card_id: str) -> str:
    return f"hotpost:cards:events:{day}:{card_id}"


def _category_events_key(day: str, category_id: str) -> str:
    return f"hotpost:cards:events:{day}:category:{category_id}"


async def record_event(redis: Redis, *, event_type: str, card_id:Optional[ str] = None, category_id:Optional[ str] = None) -> None:
    day = time.strftime("%Y-%m-%d")
    await redis.hincrby(_events_key(day), event_type, 1)
    if card_id:
        await redis.hincrby(_card_events_key(day, card_id), event_type, 1)
    if category_id:
        await redis.hincrby(_category_events_key(day, category_id), event_type, 1)
