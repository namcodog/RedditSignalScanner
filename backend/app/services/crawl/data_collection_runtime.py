from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Sequence

from app.services.crawl.data_collection_support import (
    CollectionResult,
    coerce_api_posts,
    is_cache_stale,
    normalise_subreddits,
)
from app.services.infrastructure.reddit_client import RedditPost

if TYPE_CHECKING:
    from app.services.analysis import Community


@dataclass(slots=True)
class DataCollectionRuntimeInput:
    communities: Sequence["Community"] | Sequence[str]
    limit_per_subreddit: int
    cache_stale_hours: int
    stale_fallback_enabled: bool


@dataclass(slots=True)
class DataCollectionRuntimeDeps:
    cache_get: Callable[[str], Awaitable[list[RedditPost] | None]]
    cache_set: Callable[[str, Sequence[RedditPost]], Awaitable[None]]
    load_hot_posts: Callable[[Sequence[str], int], Awaitable[Dict[str, List[RedditPost]]]]
    load_cold_posts: Callable[[Sequence[str], int], Awaitable[Dict[str, List[RedditPost]]]]
    fetch_subreddit_posts: Callable[[str, int], Awaitable[Sequence[Any]]]
    logger: logging.Logger


async def _fetch_subreddit_posts_compat(
    fetcher: Callable[..., Awaitable[Sequence[Any]]],
    subreddit: str,
    limit: int,
) -> Sequence[Any]:
    try:
        return await fetcher(subreddit, limit=limit)
    except TypeError as exc:
        if "unexpected keyword argument 'limit'" not in str(exc):
            raise
        return await fetcher(subreddit, limit)


async def collect_posts_with_fallback(
    *,
    runtime_input: DataCollectionRuntimeInput,
    deps: DataCollectionRuntimeDeps,
) -> CollectionResult:
    subreddits = normalise_subreddits(runtime_input.communities)
    if not subreddits:
        return CollectionResult(
            total_posts=0,
            cache_hits=0,
            api_calls=0,
            cache_hit_rate=0.0,
            posts_by_subreddit={},
            cached_subreddits=set(),
        )

    cached_subreddits: set[str] = set()
    stale_cache_subreddits: set[str] = set()
    stale_cache_fallback_subreddits: set[str] = set()
    stale_cache_candidates: Dict[str, List[RedditPost]] = {}
    api_failures: list[dict[str, str]] = []
    posts_by_subreddit: Dict[str, List[RedditPost]] = {}

    for subreddit in subreddits:
        try:
            cached = await deps.cache_get(subreddit)
        except Exception as exc:
            deps.logger.warning(
                "Redis 缓存读取失败，改用后备存储: subreddit=%s",
                subreddit,
                exc_info=exc,
            )
            cached = None
        if not cached:
            continue
        trimmed = list(cached[: runtime_input.limit_per_subreddit])
        if is_cache_stale(
            trimmed,
            cache_stale_hours=runtime_input.cache_stale_hours,
        ):
            stale_cache_subreddits.add(subreddit)
            stale_cache_candidates[subreddit] = trimmed
            continue
        posts_by_subreddit[subreddit] = trimmed
        cached_subreddits.add(subreddit)

    missing = [name for name in subreddits if name not in posts_by_subreddit]

    if missing:
        hot_hits = await deps.load_hot_posts(missing, runtime_input.limit_per_subreddit)
        for subreddit, posts in hot_hits.items():
            if not posts:
                continue
            trimmed = list(posts[: runtime_input.limit_per_subreddit])
            posts_by_subreddit[subreddit] = trimmed
            cached_subreddits.add(subreddit)
            try:
                await deps.cache_set(subreddit, trimmed)
            except Exception as exc:
                deps.logger.warning(
                    "写入缓存失败，将继续使用后备数据: subreddit=%s",
                    subreddit,
                    exc_info=exc,
                )

    missing_after_hot = [name for name in subreddits if name not in posts_by_subreddit]
    if missing_after_hot:
        cold_hits = await deps.load_cold_posts(
            missing_after_hot,
            runtime_input.limit_per_subreddit,
        )
        for subreddit, posts in cold_hits.items():
            if not posts:
                continue
            trimmed = list(posts[: runtime_input.limit_per_subreddit])
            posts_by_subreddit[subreddit] = trimmed
            cached_subreddits.add(subreddit)
            try:
                await deps.cache_set(subreddit, trimmed)
            except Exception as exc:
                deps.logger.warning(
                    "写入缓存失败，将继续使用后备数据: subreddit=%s",
                    subreddit,
                    exc_info=exc,
                )

    missing_after_cold = [
        name for name in subreddits if name not in posts_by_subreddit
    ]
    api_calls = 0

    fetch_coroutines = [
        _fetch_subreddit_posts_compat(
            deps.fetch_subreddit_posts,
            subreddit[2:] if subreddit.lower().startswith("r/") else subreddit,
            runtime_input.limit_per_subreddit,
        )
        for subreddit in missing_after_cold
    ]
    results = await asyncio.gather(*fetch_coroutines, return_exceptions=True)

    for subreddit, result in zip(missing_after_cold, results):
        if isinstance(result, Exception):
            error_text = str(result)
            reason = "rate_limit" if "rate limit" in error_text.lower() else "error"
            api_failures.append(
                {
                    "subreddit": subreddit,
                    "error": error_text,
                    "reason": reason,
                }
            )
            if (
                runtime_input.stale_fallback_enabled
                and subreddit in stale_cache_candidates
            ):
                posts_by_subreddit[subreddit] = list(
                    stale_cache_candidates[subreddit][: runtime_input.limit_per_subreddit]
                )
                stale_cache_fallback_subreddits.add(subreddit)
            continue

        posts = coerce_api_posts(result)
        posts_by_subreddit[subreddit] = posts
        try:
            await deps.cache_set(subreddit, posts)
        except Exception as exc:
            deps.logger.warning(
                "写入缓存失败，将继续使用 API 数据: subreddit=%s",
                subreddit,
                exc_info=exc,
            )
        api_calls += 1

    total_posts = sum(len(posts) for posts in posts_by_subreddit.values())
    cache_hits = len(cached_subreddits)
    cache_hit_rate = cache_hits / len(subreddits) if subreddits else 0.0

    return CollectionResult(
        total_posts=total_posts,
        cache_hits=cache_hits,
        api_calls=api_calls,
        cache_hit_rate=cache_hit_rate,
        posts_by_subreddit=posts_by_subreddit,
        cached_subreddits=cached_subreddits,
        stale_cache_subreddits=stale_cache_subreddits,
        stale_cache_fallback_subreddits=stale_cache_fallback_subreddits,
        api_failures=api_failures,
    )


__all__ = [
    "DataCollectionRuntimeDeps",
    "DataCollectionRuntimeInput",
    "collect_posts_with_fallback",
]
