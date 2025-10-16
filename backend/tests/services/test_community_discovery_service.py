"""Tests for Community Discovery Service (PRD-09 Warmup Period)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_pool import PendingCommunity
from app.services.community_discovery import CommunityDiscoveryService
from app.services.reddit_client import RedditPost


@pytest.fixture
def mock_reddit_client() -> AsyncMock:
    """Create a mock Reddit API client."""
    client = AsyncMock()
    client.search_posts = AsyncMock()
    return client


@pytest.fixture
def sample_reddit_posts() -> List[RedditPost]:
    """Create sample Reddit posts for testing."""
    return [
        RedditPost(
            id="post1",
            title="AI-powered note-taking app",
            selftext="Great app for researchers",
            score=100,
            num_comments=50,
            created_utc=1234567890.0,
            subreddit="productivity",
            author="user1",
            url="https://reddit.com/r/productivity/post1",
            permalink="/r/productivity/comments/post1",
        ),
        RedditPost(
            id="post2",
            title="Best note-taking tools",
            selftext="I love this AI app",
            score=80,
            num_comments=30,
            created_utc=1234567891.0,
            subreddit="productivity",
            author="user2",
            url="https://reddit.com/r/productivity/post2",
            permalink="/r/productivity/comments/post2",
        ),
        RedditPost(
            id="post3",
            title="Research tools for students",
            selftext="AI is changing everything",
            score=120,
            num_comments=60,
            created_utc=1234567892.0,
            subreddit="students",
            author="user3",
            url="https://reddit.com/r/students/post3",
            permalink="/r/students/comments/post3",
        ),
    ]


class TestCommunityDiscoveryService:
    """Test CommunityDiscoveryService functionality."""

    @pytest.mark.asyncio
    async def test_discover_from_product_description_success(
        self,
        db_session: AsyncSession,
        mock_reddit_client: AsyncMock,
        sample_reddit_posts: List[RedditPost],
    ) -> None:
        """Test successful community discovery."""
        product_description = "AI-powered note-taking app for researchers and students"

        # Mock Reddit search to return sample posts
        mock_reddit_client.search_posts.return_value = sample_reddit_posts

        service = CommunityDiscoveryService(
            db=db_session,
            reddit_client=mock_reddit_client,
            max_keywords=5,
            posts_per_keyword=10,
            min_community_mentions=2,
        )

        # Execute (task_id=None for tests)
        communities = await service.discover_from_product_description(
            task_id=None,
            product_description=product_description,
        )

        # Verify
        assert isinstance(communities, list)
        assert len(communities) > 0
        assert "productivity" in communities  # Appears 2 times

        # Verify Reddit search was called
        assert mock_reddit_client.search_posts.called

    @pytest.mark.asyncio
    async def test_discover_with_empty_description(
        self,
        db_session: AsyncSession,
        mock_reddit_client: AsyncMock,
    ) -> None:
        """Test that empty description raises ValueError."""
        service = CommunityDiscoveryService(
            db=db_session,
            reddit_client=mock_reddit_client,
        )

        with pytest.raises(ValueError, match="must contain at least 10 characters"):
            await service.discover_from_product_description(
                task_id=uuid4(),
                product_description="",
            )

    @pytest.mark.asyncio
    async def test_extract_communities_counts_correctly(
        self,
        db_session: AsyncSession,
        mock_reddit_client: AsyncMock,
        sample_reddit_posts: List[RedditPost],
    ) -> None:
        """Test that communities are counted correctly."""
        service = CommunityDiscoveryService(
            db=db_session,
            reddit_client=mock_reddit_client,
            min_community_mentions=1,
        )

        communities = service._extract_communities(sample_reddit_posts)

        assert communities["productivity"] == 2
        assert communities["students"] == 1

    @pytest.mark.asyncio
    async def test_record_discoveries_creates_new_communities(
        self,
        db_session: AsyncSession,
        mock_reddit_client: AsyncMock,
    ) -> None:
        """Test that new communities are recorded to database."""
        keywords = ["ai", "note", "taking"]
        communities = {"productivity": 5}

        service = CommunityDiscoveryService(
            db=db_session,
            reddit_client=mock_reddit_client,
        )

        await service._record_discoveries(None, keywords, communities)

        # Verify community was created
        stmt = select(PendingCommunity).where(PendingCommunity.name == "productivity")
        result = await db_session.execute(stmt)
        pending = result.scalar_one_or_none()

        assert pending is not None
        assert pending.discovered_count == 5
        assert pending.discovered_from_keywords is not None
        assert set(pending.discovered_from_keywords["keywords"]) == set(keywords)
        assert pending.status == "pending"
        assert pending.discovered_from_task_id is None

    @pytest.mark.asyncio
    async def test_record_discoveries_updates_existing_communities(
        self,
        db_session: AsyncSession,
        mock_reddit_client: AsyncMock,
    ) -> None:
        """Test that existing communities are updated."""
        keywords1 = ["ai", "note"]
        keywords2 = ["research", "tool"]

        # Create existing community
        now = datetime.now(timezone.utc)
        existing = PendingCommunity(
            name="productivity",
            discovered_from_keywords={"keywords": keywords1, "mention_count": 3},
            discovered_count=3,
            first_discovered_at=now,
            last_discovered_at=now,
            status="pending",
            discovered_from_task_id=None,
        )
        db_session.add(existing)
        await db_session.commit()

        # Discover again
        service = CommunityDiscoveryService(
            db=db_session,
            reddit_client=mock_reddit_client,
        )

        await service._record_discoveries(None, keywords2, {"productivity": 5})

        # Verify community was updated
        await db_session.refresh(existing)
        assert existing.discovered_count == 8  # 3 + 5
        assert existing.last_discovered_at > now
        # Keywords should be merged
        all_keywords = set(existing.discovered_from_keywords["keywords"])
        assert "ai" in all_keywords
        assert "note" in all_keywords
        assert "research" in all_keywords
        assert "tool" in all_keywords


class TestCommunityDiscoveryIntegration:
    """Integration tests for Community Discovery Service."""

    @pytest.mark.asyncio
    async def test_full_discovery_workflow(
        self,
        db_session: AsyncSession,
        mock_reddit_client: AsyncMock,
    ) -> None:
        """Test complete discovery workflow from description to database."""
        product_description = """
        Our AI-powered note-taking application helps researchers and students
        organize their knowledge. Features include automatic tagging,
        smart search, and collaborative editing.
        """

        # Mock Reddit posts
        posts = [
            RedditPost(
                id=f"post{i}",
                title=f"Post {i}",
                selftext="Content",
                score=100,
                num_comments=50,
                created_utc=1234567890.0 + i,
                subreddit="productivity" if i < 3 else "students",
                author=f"user{i}",
                url=f"https://reddit.com/post{i}",
                permalink=f"/r/sub/post{i}",
            )
            for i in range(5)
        ]
        mock_reddit_client.search_posts.return_value = posts

        service = CommunityDiscoveryService(
            db=db_session,
            reddit_client=mock_reddit_client,
            min_community_mentions=2,
        )

        # Execute (task_id=None for tests)
        communities = await service.discover_from_product_description(
            task_id=None,
            product_description=product_description,
        )

        # Verify
        assert "productivity" in communities
        assert "students" in communities

        # Verify database records
        stmt = select(PendingCommunity)
        result = await db_session.execute(stmt)
        pending = result.scalars().all()

        assert len(pending) >= 2
        assert any(p.name == "productivity" for p in pending)
        assert any(p.name == "students" for p in pending)

