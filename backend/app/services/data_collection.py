from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Sequence, cast

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
        self, reddit_client: RedditAPIClient, cache_manager: CacheManager
    ) -> None:
        self.reddit = reddit_client
        self.cache = cache_manager

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

        # Pre-calculate hit rate to align with monitoring expectations.
        preflight_cache_rate = self.cache.calculate_cache_hit_rate(subreddits)

        for subreddit in subreddits:
            cached = self.cache.get_cached_posts(subreddit)
            if cached:
                posts_by_subreddit[subreddit] = cached
                cached_subreddits.add(subreddit)

        cache_hits = len(cached_subreddits)
        cache_hit_rate = (
            cache_hits / len(subreddits) if subreddits else preflight_cache_rate
        )
        missing = [name for name in subreddits if name not in cached_subreddits]
        api_calls = 0

        if missing:
            # Reddit API 期望的是不带 "r/" 前缀的社区名
            def _api_name(name: str) -> str:
                key = name.strip()
                return key[2:] if key.lower().startswith("r/") else key

            fetch_coroutines = [
                self.reddit.fetch_subreddit_posts(
                    _api_name(subreddit),
                    limit=limit_per_subreddit,
                )
                for subreddit in missing
            ]

            results = await asyncio.gather(*fetch_coroutines, return_exceptions=True)
            for subreddit, result in zip(missing, results):
                if isinstance(result, Exception):
                    raise RuntimeError(
                        f"Failed to fetch subreddit {subreddit}"
                    ) from result

                posts = list(cast(List[RedditPost], result))
                posts_by_subreddit[subreddit] = posts
                self.cache.set_cached_posts(subreddit, posts)
                api_calls += 1

        total_posts = sum(len(posts) for posts in posts_by_subreddit.values())

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


__all__ = ["CollectionResult", "DataCollectionService"]
