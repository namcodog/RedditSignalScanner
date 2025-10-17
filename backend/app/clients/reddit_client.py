"""Reddit API Client Wrapper.

Provides async interface to Reddit API with rate limiting and error handling.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import praw  # type: ignore[import-untyped]
from aiolimiter import AsyncLimiter
from praw.exceptions import PRAWException  # type: ignore[import-untyped]
from praw.models import Subreddit  # type: ignore[import-untyped]

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedditClient:
    """Async wrapper for Reddit API with rate limiting.

    Reddit API limits: 60 requests per minute
    We use 58 req/min to stay safe.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Initialize Reddit client.

        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            user_agent: User agent string
        """
        self.client_id = client_id or settings.REDDIT_CLIENT_ID
        self.client_secret = client_secret or settings.REDDIT_CLIENT_SECRET
        self.user_agent = user_agent or "RedditSignalScanner/1.0"

        # Rate limiter: 58 requests per minute
        self.rate_limiter = AsyncLimiter(max_rate=58, time_period=60)

        # Initialize PRAW client
        self.reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent,
        )

        logger.info(f"Reddit client initialized with user agent: {self.user_agent}")

    async def fetch_subreddit_posts(
        self,
        subreddit_name: str,
        limit: int = 100,
        time_filter: str = "week",
    ) -> list[dict[str, Any]]:
        """Fetch posts from a subreddit.

        Args:
            subreddit_name: Name of subreddit (without r/)
            limit: Maximum number of posts to fetch (default: 100)
            time_filter: Time filter (hour, day, week, month, year, all)

        Returns:
            list: List of post dictionaries

        Raises:
            ValueError: If subreddit name is invalid
            PRAWException: If Reddit API error occurs
        """
        # Validate subreddit name
        subreddit_name = subreddit_name.strip().lower()
        if subreddit_name.startswith("r/"):
            subreddit_name = subreddit_name[2:]

        if not subreddit_name:
            raise ValueError("Subreddit name cannot be empty")

        logger.info(
            f"Fetching posts from r/{subreddit_name} (limit={limit}, time_filter={time_filter})"
        )

        try:
            # Rate limit
            async with self.rate_limiter:
                # Fetch subreddit
                subreddit = await asyncio.to_thread(
                    self.reddit.subreddit, subreddit_name
                )

                # Fetch top posts
                posts = await asyncio.to_thread(
                    lambda: list(subreddit.top(time_filter=time_filter, limit=limit))
                )

            # Convert to dict
            post_dicts = []
            for post in posts:
                post_dict = await self._post_to_dict(post)
                post_dicts.append(post_dict)

            logger.info(f"Fetched {len(post_dicts)} posts from r/{subreddit_name}")
            return post_dicts

        except PRAWException as e:
            logger.error(f"Reddit API error for r/{subreddit_name}: {e}")
            raise

    async def fetch_subreddit_info(
        self,
        subreddit_name: str,
    ) -> dict[str, Any]:
        """Fetch subreddit information.

        Args:
            subreddit_name: Name of subreddit (without r/)

        Returns:
            dict: Subreddit information

        Raises:
            ValueError: If subreddit name is invalid
            PRAWException: If Reddit API error occurs
        """
        # Validate subreddit name
        subreddit_name = subreddit_name.strip().lower()
        if subreddit_name.startswith("r/"):
            subreddit_name = subreddit_name[2:]

        if not subreddit_name:
            raise ValueError("Subreddit name cannot be empty")

        logger.info(f"Fetching info for r/{subreddit_name}")

        try:
            # Rate limit
            async with self.rate_limiter:
                # Fetch subreddit
                subreddit = await asyncio.to_thread(
                    self.reddit.subreddit, subreddit_name
                )

                # Get info
                info = {
                    "name": subreddit.display_name,
                    "title": subreddit.title,
                    "description": subreddit.public_description,
                    "subscribers": subreddit.subscribers,
                    "created_utc": datetime.fromtimestamp(
                        subreddit.created_utc, tz=timezone.utc
                    ),
                    "over18": subreddit.over18,
                    "url": f"https://reddit.com{subreddit.url}",
                }

            logger.info(
                f"Fetched info for r/{subreddit_name}: {info['subscribers']} subscribers"
            )
            return info

        except PRAWException as e:
            logger.error(f"Reddit API error for r/{subreddit_name}: {e}")
            raise

    async def search_subreddits(
        self,
        query: str,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Search for subreddits.

        Args:
            query: Search query
            limit: Maximum number of results (default: 25)

        Returns:
            list: List of subreddit dictionaries

        Raises:
            ValueError: If query is empty
            PRAWException: If Reddit API error occurs
        """
        query = query.strip()
        if not query:
            raise ValueError("Search query cannot be empty")

        logger.info(f"Searching subreddits for: {query} (limit={limit})")

        try:
            # Rate limit
            async with self.rate_limiter:
                # Search subreddits
                results = await asyncio.to_thread(
                    lambda: list(self.reddit.subreddits.search(query, limit=limit))
                )

            # Convert to dict
            subreddit_dicts = []
            for subreddit in results:
                subreddit_dict = {
                    "name": subreddit.display_name,
                    "title": subreddit.title,
                    "description": subreddit.public_description,
                    "subscribers": subreddit.subscribers,
                    "url": f"https://reddit.com{subreddit.url}",
                }
                subreddit_dicts.append(subreddit_dict)

            logger.info(f"Found {len(subreddit_dicts)} subreddits for query: {query}")
            return subreddit_dicts

        except PRAWException as e:
            logger.error(f"Reddit API error for search '{query}': {e}")
            raise

    async def _post_to_dict(self, post: Any) -> dict[str, Any]:
        """Convert PRAW post to dictionary.

        Args:
            post: PRAW submission object

        Returns:
            dict: Post dictionary
        """
        return {
            "id": post.id,
            "title": post.title,
            "author": str(post.author) if post.author else "[deleted]",
            "created_utc": datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
            "score": post.score,
            "upvote_ratio": post.upvote_ratio,
            "num_comments": post.num_comments,
            "url": post.url,
            "permalink": f"https://reddit.com{post.permalink}",
            "selftext": post.selftext,
            "is_self": post.is_self,
            "over_18": post.over_18,
            "spoiler": post.spoiler,
            "stickied": post.stickied,
            "subreddit": post.subreddit.display_name,
        }

    async def get_rate_limit_status(self) -> dict[str, Any]:
        """Get current rate limit status.

        Returns:
            dict: Rate limit status
        """
        return {
            "max_rate": self.rate_limiter.max_rate,
            "time_period": self.rate_limiter.time_period,
            "has_capacity": self.rate_limiter.has_capacity,
        }

    async def close(self) -> None:
        """Close Reddit client."""
        logger.info("Closing Reddit client")
        # PRAW doesn't require explicit closing
