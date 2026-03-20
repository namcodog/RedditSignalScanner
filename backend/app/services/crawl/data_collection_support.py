from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Sequence

from app.models.posts_storage import PostHot, PostRaw
from app.services.infrastructure.reddit_client import RedditPost


@dataclass(slots=True)
class CollectionResult:
    total_posts: int
    cache_hits: int
    api_calls: int
    cache_hit_rate: float
    posts_by_subreddit: Dict[str, List[RedditPost]]
    cached_subreddits: set[str]
    stale_cache_subreddits: set[str] = field(default_factory=set)
    stale_cache_fallback_subreddits: set[str] = field(default_factory=set)
    api_failures: list[dict[str, str]] = field(default_factory=list)


def read_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def read_truthy_env(name: str, *, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y"}


def is_cache_stale(posts: Sequence[RedditPost], *, cache_stale_hours: int) -> bool:
    if cache_stale_hours <= 0:
        return False
    newest_ts = 0.0
    for post in posts:
        try:
            newest_ts = max(newest_ts, float(post.created_utc or 0.0))
        except (TypeError, ValueError):
            continue
    if newest_ts <= 0:
        return True
    newest_dt = datetime.fromtimestamp(newest_ts, tz=timezone.utc)
    return datetime.now(timezone.utc) - newest_dt > timedelta(hours=cache_stale_hours)


def normalise_subreddits(communities: Sequence[Any]) -> List[str]:
    if not communities:
        return []

    from app.utils.subreddit import normalize_subreddit_name

    names: List[str] = []
    seen: set[str] = set()

    for entry in communities:
        subreddit = getattr(entry, "name", entry)
        canonical = normalize_subreddit_name(str(subreddit))
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        names.append(canonical)

    return names


def normalise_timestamp(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def map_hot_record(record: PostHot) -> RedditPost:
    metadata = record.extra_data or {}
    permalink = str(
        metadata.get("permalink")
        or f"/r/{record.subreddit}/comments/{record.source_post_id}"
    )
    url = str(metadata.get("url") or f"https://reddit.com{permalink}")
    author = str(record.author_name or metadata.get("author") or "unknown")

    return RedditPost(
        id=str(record.source_post_id),
        title=str(record.title or ""),
        selftext=str(record.body or ""),
        score=int(record.score or 0),
        num_comments=int(record.num_comments or 0),
        created_utc=normalise_timestamp(record.created_at),
        subreddit=str(record.subreddit),
        author=author,
        url=url,
        permalink=permalink,
    )


def map_cold_record(record: PostRaw) -> RedditPost:
    metadata = record.extra_data or {}
    permalink = str(
        metadata.get("permalink")
        or record.url
        or f"/r/{record.subreddit}/comments/{record.source_post_id}"
    )
    url = str(record.url or metadata.get("url") or f"https://reddit.com{permalink}")
    author = str(record.author_name or metadata.get("author") or "unknown")

    return RedditPost(
        id=str(record.source_post_id),
        title=str(record.title or ""),
        selftext=str(record.body or ""),
        score=int(record.score or 0),
        num_comments=int(record.num_comments or 0),
        created_utc=normalise_timestamp(record.created_at),
        subreddit=str(record.subreddit),
        author=author,
        url=url,
        permalink=permalink,
    )


def coerce_api_posts(items: Sequence[Any]) -> List[RedditPost]:
    posts: List[RedditPost] = []
    for item in items:
        if isinstance(item, RedditPost):
            posts.append(item)
            continue
        if not isinstance(item, dict):
            continue
        try:
            posts.append(
                RedditPost(
                    id=str(item.get("id", "")),
                    title=str(item.get("title", "")),
                    selftext=str(item.get("selftext", "")),
                    score=int(item.get("score", 0) or 0),
                    num_comments=int(item.get("num_comments", 0) or 0),
                    created_utc=float(item.get("created_utc", 0) or 0.0),
                    subreddit=str(item.get("subreddit", "")),
                    author=str(item.get("author", "")),
                    url=str(item.get("url", "")),
                    permalink=str(item.get("permalink", "")),
                )
            )
        except Exception:
            continue
    return posts


__all__ = [
    "CollectionResult",
    "coerce_api_posts",
    "is_cache_stale",
    "map_cold_record",
    "map_hot_record",
    "normalise_subreddits",
    "normalise_timestamp",
    "read_int_env",
    "read_truthy_env",
]
