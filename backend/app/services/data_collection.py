from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Callable, Dict, List, Sequence, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionFactory
from app.models.posts_storage import PostHot, PostRaw
from app.services.cache_manager import CacheManager
from app.services.reddit_client import RedditAPIClient, RedditPost

if TYPE_CHECKING:
    from app.services.analysis import Community


@dataclass(slots=True)
class CollectionResult:
    total_posts: int
    cache_hits: int
    api_calls: int
    cache_hit_rate: float
    posts_by_subreddit: Dict[str, List[RedditPost]]
    cached_subreddits: set[str]


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

    async def collect_posts(
        self,
        communities: Sequence["Community"] | Sequence[str],
        *,
        limit_per_subreddit: int = 100,
    ) -> CollectionResult:
        """
        Collect posts using cached data when available and falling back to live API calls.
        """
        subreddits = self._normalise_subreddits(communities)
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
        posts_by_subreddit: Dict[str, List[RedditPost]] = {}

        for subreddit in subreddits:
            try:
                cached = await self.cache.get_cached_posts(subreddit)
            except Exception as exc:
                self._logger.warning(
                    "Redis 缓存读取失败，改用后备存储: subreddit=%s", subreddit, exc_info=exc
                )
                cached = None
            if cached:
                trimmed = list(cached[:limit_per_subreddit])
                posts_by_subreddit[subreddit] = trimmed
                cached_subreddits.add(subreddit)

        missing = [name for name in subreddits if name not in posts_by_subreddit]
        api_calls = 0

        if missing:
            hot_hits = await self._load_hot_posts(missing, limit_per_subreddit)
            for subreddit, posts in hot_hits.items():
                if not posts:
                    continue
                trimmed = list(posts[:limit_per_subreddit])
                posts_by_subreddit[subreddit] = trimmed
                cached_subreddits.add(subreddit)
                try:
                    await self.cache.set_cached_posts(subreddit, trimmed)
                except Exception as exc:
                    self._logger.warning(
                        "写入缓存失败，将继续使用后备数据: subreddit=%s", subreddit, exc_info=exc
                    )

        missing_after_hot = [
            name for name in subreddits if name not in posts_by_subreddit
        ]

        if missing_after_hot:
            cold_hits = await self._load_cold_posts(
                missing_after_hot, limit_per_subreddit
            )
            for subreddit, posts in cold_hits.items():
                if not posts:
                    continue
                trimmed = list(posts[:limit_per_subreddit])
                posts_by_subreddit[subreddit] = trimmed
                cached_subreddits.add(subreddit)
                try:
                    await self.cache.set_cached_posts(subreddit, trimmed)
                except Exception as exc:
                    self._logger.warning(
                        "写入缓存失败，将继续使用后备数据: subreddit=%s", subreddit, exc_info=exc
                    )

        missing_after_cold = [
            name for name in subreddits if name not in posts_by_subreddit
        ]

        if missing_after_cold:
            # Reddit API 期望的是不带 "r/" 前缀的社区名
            def _api_name(name: str) -> str:
                key = name.strip()
                return key[2:] if key.lower().startswith("r/") else key

            fetch_coroutines = [
                self.reddit.fetch_subreddit_posts(
                    _api_name(subreddit),
                    limit=limit_per_subreddit,
                )
                for subreddit in missing_after_cold
            ]

            results = await asyncio.gather(*fetch_coroutines, return_exceptions=True)
            for subreddit, result in zip(missing_after_cold, results):
                if isinstance(result, Exception):
                    raise RuntimeError(
                        f"Failed to fetch subreddit {subreddit}"
                    ) from result

                posts = list(cast(List[RedditPost], result))
                posts_by_subreddit[subreddit] = posts
                try:
                    await self.cache.set_cached_posts(subreddit, posts)
                except Exception as exc:
                    self._logger.warning(
                        "写入缓存失败，将继续使用 API 数据: subreddit=%s", subreddit, exc_info=exc
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
        )

    @staticmethod
    def _normalise_subreddits(
        communities: Sequence["Community"] | Sequence[str],
    ) -> List[str]:
        if not communities:
            return []

        names: List[str] = []
        seen: set[str] = set()

        for entry in communities:
            subreddit = getattr(entry, "name", entry)
            subreddit = str(subreddit)
            key = subreddit.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            names.append(subreddit.strip())

        return names

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
            created_utc=DataCollectionService._normalise_timestamp(record.created_at),
            subreddit=str(record.subreddit),
            author=author,
            url=url,
            permalink=permalink,
        )

    @staticmethod
    def _map_cold_record(record: PostRaw) -> RedditPost:
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
            created_utc=DataCollectionService._normalise_timestamp(record.created_at),
            subreddit=str(record.subreddit),
            author=author,
            url=url,
            permalink=permalink,
        )

    @staticmethod
    def _normalise_timestamp(value: datetime) -> float:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()


__all__ = ["CollectionResult", "DataCollectionService"]
