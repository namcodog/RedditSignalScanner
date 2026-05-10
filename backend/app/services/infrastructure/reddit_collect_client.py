from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditAPIError, RedditPost
from app.services.infrastructure.sociavault_reddit_client import SociaVaultRedditClient


def _should_fallback_to_sociavault(exc: RedditAPIError) -> bool:
    message = str(exc).lower()
    needles = [
        "rate limit",
        "timed out",
        "temporarily unavailable",
        "connection failed",
    ]
    return any(needle in message for needle in needles)


class CollectRedditClient:
    def __init__(
        self,
        primary: RedditAPIClient,
        fallback: SociaVaultRedditClient | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self._stats: dict[str, int] = {
            "primary_post_requests": 0,
            "fallback_post_requests": 0,
            "primary_comment_requests": 0,
            "fallback_comment_requests": 0,
            "discover_assist_hits": 0,
            "comment_assist_hits": 0,
            "rescue_hits": 0,
        }

    async def __aenter__(self) -> "CollectRedditClient":
        await self.primary.__aenter__()
        if self.fallback is not None:
            await self.fallback.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.fallback is not None:
            await self.fallback.__aexit__(exc_type, exc, tb)
        await self.primary.__aexit__(exc_type, exc, tb)

    async def close(self) -> None:
        if self.fallback is not None:
            await self.fallback.close()
        await self.primary.close()

    def should_skip_comment_fetch(self) -> bool:
        if self.fallback is not None:
            return False
        return self.primary.should_skip_comment_fetch()

    def get_ratelimit_snapshot(self) -> dict[str, Any]:
        if hasattr(self.primary, "get_ratelimit_snapshot"):
            return self.primary.get_ratelimit_snapshot()  # type: ignore[no-any-return]
        return {}

    def get_collect_stats(self) -> dict[str, int]:
        return dict(self._stats)

    async def fetch_subreddit_posts(
        self,
        subreddit: str,
        *,
        limit: int = 25,
        time_filter: str = "day",
        sort: str = "hot",
        after: str | None = None,
        prefer_fallback: bool = False,
    ) -> tuple[list[RedditPost], str | None]:
        if prefer_fallback and self.fallback is not None:
            self._stats["fallback_post_requests"] += 1
            self._stats["discover_assist_hits"] += 1
            posts, _ = await self.fallback.fetch_subreddit_posts(
                subreddit,
                limit=limit,
                time_filter=time_filter,
                sort=sort,
                after=after,
            )
            return posts, None
        try:
            self._stats["primary_post_requests"] += 1
            return await self.primary.fetch_subreddit_posts(
                subreddit,
                limit=limit,
                time_filter=time_filter,
                sort=sort,
                after=after,
            )
        except RedditAPIError as exc:
            if self.fallback is None or not _should_fallback_to_sociavault(exc):
                raise
            self._stats["fallback_post_requests"] += 1
            self._stats["rescue_hits"] += 1
            posts, _ = await self.fallback.fetch_subreddit_posts(
                subreddit,
                limit=limit,
                time_filter=time_filter,
                sort=sort,
                after=after,
            )
            return posts, None

    async def search_subreddit_page(
        self,
        subreddit: str,
        query: str,
        *,
        limit: int = 25,
        sort: str = "relevance",
        time_filter: str = "day",
        restrict_sr: bool | None = None,
        syntax: str | None = None,
        after: str | None = None,
        prefer_fallback: bool = False,
    ) -> tuple[list[RedditPost], str | None]:
        if prefer_fallback and self.fallback is not None:
            self._stats["fallback_post_requests"] += 1
            self._stats["discover_assist_hits"] += 1
            posts, _ = await self.fallback.search_subreddit_page(
                subreddit,
                query,
                limit=limit,
                sort=sort,
                time_filter=time_filter,
                restrict_sr=restrict_sr,
                syntax=syntax,
                after=after,
            )
            return posts, None
        try:
            self._stats["primary_post_requests"] += 1
            return await self.primary.search_subreddit_page(
                subreddit,
                query,
                limit=limit,
                sort=sort,
                time_filter=time_filter,
                restrict_sr=restrict_sr,
                syntax=syntax,
                after=after,
            )
        except RedditAPIError as exc:
            if self.fallback is None or not _should_fallback_to_sociavault(exc):
                raise
            self._stats["fallback_post_requests"] += 1
            self._stats["rescue_hits"] += 1
            posts, _ = await self.fallback.search_subreddit_page(
                subreddit,
                query,
                limit=limit,
                sort=sort,
                time_filter=time_filter,
                restrict_sr=restrict_sr,
                syntax=syntax,
                after=after,
            )
            return posts, None

    async def fetch_post_comments(
        self,
        post_id: str,
        *,
        sort: str = "confidence",
        depth: int = 1,
        limit: int = 50,
        mode: str = "topn",
        comment_timeout: float | None = None,
        smart_config: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if self.fallback is not None and self.primary.should_skip_comment_fetch():
            self._stats["fallback_comment_requests"] += 1
            self._stats["comment_assist_hits"] += 1
            return await self.fallback.fetch_post_comments(
                post_id,
                sort=sort,
                depth=depth,
                limit=limit,
                mode=mode,
                comment_timeout=comment_timeout,
                smart_config=smart_config,
            )
        try:
            self._stats["primary_comment_requests"] += 1
            comments = await self.primary.fetch_post_comments(
                post_id,
                sort=sort,
                depth=depth,
                limit=limit,
                mode=mode,
                comment_timeout=comment_timeout,
                smart_config=smart_config,
            )
            if comments or self.fallback is None:
                return comments
            self._stats["fallback_comment_requests"] += 1
            self._stats["comment_assist_hits"] += 1
            return await self.fallback.fetch_post_comments(
                post_id,
                sort=sort,
                depth=depth,
                limit=limit,
                mode=mode,
                comment_timeout=comment_timeout,
                smart_config=smart_config,
            )
        except RedditAPIError as exc:
            if self.fallback is None or not _should_fallback_to_sociavault(exc):
                raise
            self._stats["fallback_comment_requests"] += 1
            self._stats["rescue_hits"] += 1
            return await self.fallback.fetch_post_comments(
                post_id,
                sort=sort,
                depth=depth,
                limit=limit,
                mode=mode,
                comment_timeout=comment_timeout,
                smart_config=smart_config,
            )


def build_collect_reddit_client(
    *,
    request_timeout: float,
    search_timeout: float,
    max_concurrency: int,
    low_quota_remaining_threshold: int,
    low_quota_cooldown_seconds: float,
    stop_comment_fetch_below_remaining: int,
    max_consecutive_rate_limit_errors: int,
) -> CollectRedditClient:
    primary = RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        request_timeout=request_timeout,
        search_timeout=search_timeout,
        max_concurrency=max_concurrency,
        low_quota_remaining_threshold=low_quota_remaining_threshold,
        low_quota_cooldown_seconds=low_quota_cooldown_seconds,
        stop_comment_fetch_below_remaining=stop_comment_fetch_below_remaining,
        max_consecutive_rate_limit_errors=max_consecutive_rate_limit_errors,
    )
    fallback: SociaVaultRedditClient | None = None
    if settings.sociavault_reddit_fallback_enabled and settings.sociavault_api_key.strip():
        fallback = SociaVaultRedditClient(
            api_key=settings.sociavault_api_key,
            base_url=settings.sociavault_base_url,
            request_timeout=max(10.0, request_timeout),
        )
    return CollectRedditClient(
        primary=primary,
        fallback=fallback,
    )


__all__ = [
    "CollectRedditClient",
    "build_collect_reddit_client",
]
