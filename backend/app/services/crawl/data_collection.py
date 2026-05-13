from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Callable, Dict, List, Sequence, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionFactory
from app.models.posts_storage import PostHot, PostRaw
from app.services.crawl.data_collection_runtime import (
    DataCollectionRuntimeDeps,
    DataCollectionRuntimeInput,
    collect_posts_with_fallback,
)
from app.services.crawl.data_collection_support import (
    CollectionResult,
    map_cold_record,
    map_hot_record,
    normalise_subreddits,
    normalise_timestamp,
    read_int_env,
    read_truthy_env,
    is_cache_stale,
)
from app.services.infrastructure.cache_manager import CacheManager
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditPost

if TYPE_CHECKING:
    from app.services.analysis import Community


class DataCollectionService:
    """
    Cache-first data collection service (PRD-03 §3.2).
    """

    def __init__(
        self,
        reddit_client: RedditAPIClient,
        cache_manager: CacheManager,
        *,
        session_factory: Callable[[], AsyncSession] | None = None,
        cold_retention_days: int = 90,
    ) -> None:
        self.reddit = reddit_client
        self.cache = cache_manager
        self._session_factory = session_factory or SessionFactory
        self._cold_retention_days = max(1, cold_retention_days)
        self._logger = logging.getLogger(__name__)
        self._cache_stale_hours = self._read_int_env(
            "DATA_COLLECTION_CACHE_STALE_HOURS", 12
        )
        self._stale_fallback_enabled = self._read_truthy_env(
            "DATA_COLLECTION_STALE_FALLBACK_ENABLED", default="1"
        )

    @staticmethod
    def _read_int_env(name: str, default: int) -> int:
        return read_int_env(name, default)

    @staticmethod
    def _read_truthy_env(name: str, *, default: str = "0") -> bool:
        return read_truthy_env(name, default=default)

    def _is_cache_stale(self, posts: Sequence[RedditPost]) -> bool:
        return is_cache_stale(
            posts,
            cache_stale_hours=self._cache_stale_hours,
        )

    async def collect_posts(
        self,
        communities: Sequence["Community"] | Sequence[str],
        *,
        limit_per_subreddit: int = 100,
    ) -> CollectionResult:
        """
        Collect posts using cached data when available and falling back to live API calls.
        """
        return await collect_posts_with_fallback(
            runtime_input=DataCollectionRuntimeInput(
                communities=communities,
                limit_per_subreddit=limit_per_subreddit,
                cache_stale_hours=self._cache_stale_hours,
                stale_fallback_enabled=self._stale_fallback_enabled,
            ),
            deps=DataCollectionRuntimeDeps(
                cache_get=self.cache.get_cached_posts,
                cache_set=self.cache.set_cached_posts,
                load_hot_posts=self._load_hot_posts,
                load_cold_posts=self._load_cold_posts,
                fetch_subreddit_posts=self.reddit.fetch_subreddit_posts,
                logger=self._logger,
            ),
        )

    @staticmethod
    def _normalise_subreddits(
        communities: Sequence["Community"] | Sequence[str],
    ) -> List[str]:
        return normalise_subreddits(cast(Sequence[object], communities))

    async def _load_hot_posts(
        self,
        subreddits: Sequence[str],
        limit_per_subreddit: int,
    ) -> Dict[str, List[RedditPost]]:
        if not subreddits:
            return {}

        async with self._session_factory() as session:
            now = datetime.now(timezone.utc)
            stmt = (
                select(PostHot)
                .where(
                    PostHot.subreddit.in_(tuple(subreddits)),
                    PostHot.expires_at >= now,
                )
                .order_by(PostHot.subreddit, PostHot.created_at.desc())
            )
            records = (await session.execute(stmt)).scalars().all()

        grouped: Dict[str, List[RedditPost]] = defaultdict(list)
        for record in records:
            bucket = grouped[record.subreddit]
            if len(bucket) >= limit_per_subreddit:
                continue
            bucket.append(self._map_hot_record(record))
        return {subreddit: posts for subreddit, posts in grouped.items() if posts}

    async def _load_cold_posts(
        self,
        subreddits: Sequence[str],
        limit_per_subreddit: int,
    ) -> Dict[str, List[RedditPost]]:
        if not subreddits:
            return {}

        async with self._session_factory() as session:
            cutoff = datetime.now(timezone.utc) - timedelta(
                days=self._cold_retention_days
            )
            stmt = (
                select(PostRaw)
                .where(
                    PostRaw.subreddit.in_(tuple(subreddits)),
                    PostRaw.is_current.is_(True),
                    PostRaw.created_at >= cutoff,
                )
                .order_by(PostRaw.subreddit, PostRaw.created_at.desc())
            )
            records = (await session.execute(stmt)).scalars().all()

        grouped: Dict[str, List[RedditPost]] = defaultdict(list)
        for record in records:
            bucket = grouped[record.subreddit]
            if len(bucket) >= limit_per_subreddit:
                continue
            bucket.append(self._map_cold_record(record))
        return {subreddit: posts for subreddit, posts in grouped.items() if posts}

    @staticmethod
    def _map_hot_record(record: PostHot) -> RedditPost:
        return map_hot_record(record)

    @staticmethod
    def _map_cold_record(record: PostRaw) -> RedditPost:
        return map_cold_record(record)

    @staticmethod
    def _normalise_timestamp(value: datetime) -> float:
        return normalise_timestamp(value)


__all__ = ["CollectionResult", "DataCollectionService"]
