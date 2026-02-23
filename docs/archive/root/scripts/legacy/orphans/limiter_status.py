#!/usr/bin/env python3
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import redis.asyncio as redis  # type: ignore

from app.core.config import get_settings


async def main() -> None:
    s = get_settings()
    key = f"reddit_api:qpm:{s.reddit_client_id or 'default'}"
    r = redis.Redis.from_url(s.reddit_cache_redis_url)
    ttl = await r.ttl(key)
    val = await r.get(key)
    now = datetime.now(timezone.utc).isoformat()
    print({
        "time": now,
        "key": key,
        "current_count": int(val) if val else 0,
        "ttl_seconds": int(ttl) if isinstance(ttl, int) else ttl,
        "limit": s.reddit_rate_limit,
        "window_seconds": int(s.reddit_rate_limit_window_seconds),
        "redis": s.reddit_cache_redis_url,
    })


if __name__ == "__main__":
    asyncio.run(main())

