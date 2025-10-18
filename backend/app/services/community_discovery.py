"""Community Discovery Service for PRD-09 Day 13-20 Warmup Period.

Discovers new Reddit communities from product descriptions by:
1. Extracting keywords using TF-IDF
2. Searching Reddit for posts matching keywords
3. Extracting and counting subreddit sources
4. Recording discoveries to pending_communities table
"""

from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_pool import PendingCommunity
from app.services.keyword_extractor import KeywordExtractor
from app.services.reddit_client import RedditAPIClient, RedditPost


class CommunityDiscoveryService:
    """Service for discovering new Reddit communities from product descriptions."""

    def __init__(
        self,
        db: AsyncSession,
        reddit_client: RedditAPIClient,
        *,
        max_keywords: int = 10,
        posts_per_keyword: int = 10,
        min_community_mentions: int = 2,
    ) -> None:
        """Initialize community discovery service.

        Args:
            db: Database session
            reddit_client: Reddit API client
            max_keywords: Maximum keywords to extract from description
            posts_per_keyword: Number of posts to fetch per keyword
            min_community_mentions: Minimum mentions required to record a community
        """
        self.db = db
        self.reddit_client = reddit_client
        self.max_keywords = max_keywords
        self.posts_per_keyword = posts_per_keyword
        self.min_community_mentions = min_community_mentions
        self.keyword_extractor = KeywordExtractor(max_features=max_keywords)

    async def discover_from_product_description(
        self,
        task_id: UUID | None,
        product_description: str,
    ) -> List[str]:
        """Discover relevant communities from product description.

        Args:
            task_id: Task ID for tracking discovery source
            product_description: Product description text

        Returns:
            List of discovered community names

        Raises:
            ValueError: If product description is invalid
        """
        if not product_description or len(product_description.strip()) < 10:
            raise ValueError("product_description must contain at least 10 characters")

        # Step 1: Extract keywords
        keywords = await self._extract_keywords(product_description)

        if not keywords:
            return []

        # Step 2: Search Reddit posts for each keyword
        posts = await self._search_reddit_posts(keywords)

        if not posts:
            return []

        # Step 3: Extract and count communities
        communities = self._extract_communities(posts)

        # Step 4: Record discoveries to database
        await self._record_discoveries(task_id, keywords, communities)

        return list(communities.keys())

    async def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text using TF-IDF.

        Args:
            text: Text to extract keywords from

        Returns:
            List of extracted keywords
        """
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        keywords = await loop.run_in_executor(
            None,
            self.keyword_extractor.extract,
            text,
            self.max_keywords,
        )
        return keywords

    async def _search_reddit_posts(self, keywords: List[str]) -> List[RedditPost]:
        """Search Reddit for posts matching keywords using Reddit Search API.

        Args:
            keywords: List of keywords to search for

        Returns:
            List of Reddit posts
        """
        if not keywords:
            return []

        all_posts: List[RedditPost] = []

        # Search for each keyword (limit to top keywords to avoid rate limits)
        search_keywords = keywords[:5]  # Use top 5 keywords

        for keyword in search_keywords:
            try:
                # Use Reddit's search API
                posts = await self.reddit_client.search_posts(
                    query=keyword,
                    limit=self.posts_per_keyword,
                    time_filter="week",
                    sort="relevance",
                )
                all_posts.extend(posts)

            except Exception:
                # If search fails for this keyword, continue with others
                # In production, we'd log this error
                continue

        # Remove duplicates (same post might match multiple keywords)
        seen_ids = set()
        unique_posts: List[RedditPost] = []
        for post in all_posts:
            if post.id not in seen_ids:
                seen_ids.add(post.id)
                unique_posts.append(post)

        return unique_posts

    def _extract_communities(self, posts: List[RedditPost]) -> Dict[str, int]:
        """Extract and count community mentions from posts.

        Args:
            posts: List of Reddit posts

        Returns:
            Dictionary mapping community names to mention counts
        """
        if not posts:
            return {}

        # Count subreddit occurrences
        subreddit_counter = Counter(post.subreddit for post in posts)

        # Filter by minimum mentions
        communities = {
            name: count
            for name, count in subreddit_counter.items()
            if count >= self.min_community_mentions
        }

        return communities

    async def _record_discoveries(
        self,
        task_id: UUID | None,
        keywords: List[str],
        communities: Dict[str, int],
    ) -> None:
        """Record discovered communities to database.

        Args:
            task_id: Task ID for tracking discovery source
            keywords: Keywords used for discovery
            communities: Dictionary mapping community names to mention counts
        """
        if not communities:
            return

        now = datetime.now(timezone.utc)

        for community_name, mention_count in communities.items():
            # Check if community already exists
            stmt = select(PendingCommunity).where(
                PendingCommunity.name == community_name
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                existing.discovered_count += mention_count
                existing.last_discovered_at = now
                # Merge keywords
                if existing.discovered_from_keywords:
                    existing_keywords = set(
                        existing.discovered_from_keywords.get("keywords", [])
                    )
                    existing_keywords.update(keywords)
                    existing.discovered_from_keywords = {
                        "keywords": list(existing_keywords),
                        "mention_count": existing.discovered_count,
                    }
            else:
                # Create new record
                new_community = PendingCommunity(
                    name=community_name,
                    discovered_from_keywords={
                        "keywords": keywords,
                        "mention_count": mention_count,
                    },
                    discovered_count=mention_count,
                    first_discovered_at=now,
                    last_discovered_at=now,
                    status="pending",
                    discovered_from_task_id=task_id,
                )
                self.db.add(new_community)

        await self.db.commit()


__all__ = ["CommunityDiscoveryService"]
