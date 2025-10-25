from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, cast

import redis.asyncio as redis

from app.services.reddit_client import RedditPost

DEFAULT_CACHE_TTL_SECONDS = 24 * 60 * 60


class RedisLike(Protocol):
    async def get(self, key: str) -> bytes | str | None:
        ...

    async def setex(self, key: str, time: int, value: str) -> bool | None:
        ...

    async def exists(self, key: str) -> int:
        ...

    async def delete(self, key: str) -> int:
        ...


class CacheManager:
    """
    Redis-backed cache manager honouring the cache-first strategy (PRD-03 §3.2).
    """

    def __init__(
        self,
        redis_client: RedisLike | None = None,
        *,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        namespace: str = "reddit:posts",
        redis_url: str | None = None,
    ) -> None:
        if redis_client is not None:
            self.redis = redis_client
        else:
            target_url = redis_url or "redis://localhost:6379/5"
            # Cast to RedisLike to satisfy mypy in absence of redis stubs
            self.redis = cast(
                RedisLike,
                redis.Redis.from_url(target_url, decode_responses=False),
            )
        self.cache_ttl = max(60, cache_ttl_seconds)
        self.namespace = namespace.strip(":")

    async def get_cached_posts(
        self,
        subreddit: str,
        *,
        max_age_hours: int = 24,
    ) -> Optional[List[RedditPost]]:
        """
        Load subreddit posts from cache if the payload is still considered fresh.
        """
        key = self._build_key(subreddit)
        raw = await self.redis.get(key)
        if raw is None:
            return None

        decoded = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        try:
            payload = json.loads(decoded)
        except json.JSONDecodeError:
            return None

        cached_at_str = payload.get("cached_at")
        posts_data = payload.get("posts", [])
        if cached_at_str is None:
            return None

        try:
            cached_at = datetime.fromisoformat(cached_at_str)
        except ValueError:
            return None

        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)

        max_age = timedelta(hours=max_age_hours)
        if datetime.now(timezone.utc) - cached_at > max_age:
            return None

        return [self._deserialize_post(item) for item in posts_data]

    async def set_cached_posts(
        self,
        subreddit: str,
        posts: Sequence[RedditPost],
    ) -> None:
        """Persist subreddit posts and timestamp."""
        key = self._build_key(subreddit)
        data = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "posts": [self._serialise_post(post) for post in posts],
        }
        await self.redis.setex(key, self.cache_ttl, json.dumps(data, ensure_ascii=False))

    async def calculate_cache_hit_rate(
        self,
        subreddits: Iterable[str],
        *,
        max_age_hours: int = 24,
    ) -> float:
        """
        Calculate the proportion of subreddits with healthy cache entries.
        """
        names = [name.strip() for name in subreddits if name and name.strip()]
        if not names:
            return 0.0

        hits = 0
        for name in names:
            posts = await self.get_cached_posts(name, max_age_hours=max_age_hours)
            if posts:
                hits += 1
        return hits / len(names)

    async def invalidate(self, subreddit: str) -> None:
        """Remove a cached entry manually."""
        await self.redis.delete(self._build_key(subreddit))

    def _build_key(self, subreddit: str) -> str:
        return f"{self.namespace}:{subreddit.lower()}"

    @staticmethod
    def _serialise_post(post: RedditPost) -> Dict[str, Any]:
        if is_dataclass(post):
            return asdict(post)
        if isinstance(post, dict):
            return post
        raise TypeError(
            "CacheManager expects RedditPost dataclasses for serialisation."
        )

    @staticmethod
    def _deserialize_post(data: Dict[str, Any]) -> RedditPost:
        return RedditPost(
            id=str(data.get("id", "")),
            title=str(data.get("title", "") or ""),
            selftext=str(data.get("selftext", "") or ""),
            score=int(data.get("score", 0) or 0),
            num_comments=int(data.get("num_comments", 0) or 0),
            created_utc=float(data.get("created_utc", 0.0) or 0.0),
            subreddit=str(data.get("subreddit", "") or ""),
            author=str(data.get("author", "unknown") or "unknown"),
            url=str(data.get("url", "") or ""),
            permalink=str(data.get("permalink", "") or ""),
        )


__all__ = ["CacheManager"]
