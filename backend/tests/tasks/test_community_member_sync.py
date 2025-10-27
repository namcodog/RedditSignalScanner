"""Tests for community member count sync task.

Related to: P1-5 (硬编码的社区成员数)
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select

from app.tasks.community_member_sync_task import (
    _sync_community_members_impl,
    _fetch_member_count,
    sync_community_member_counts,
)
from app.models.community_cache import CommunityCache


@pytest.mark.asyncio
async def test_fetch_member_count_success():
    """Test fetching member count from Reddit API."""
    # Mock Reddit client
    mock_client = AsyncMock()
    mock_client.access_token = "test_token"
    mock_client.user_agent = "test_agent"
    mock_client._request_json = AsyncMock(
        return_value={"data": {"subscribers": 1_200_000}}
    )
    
    # Test
    member_count = await _fetch_member_count(mock_client, "startups")
    
    # Verify
    assert member_count == 1_200_000
    mock_client.authenticate.assert_called_once()
    mock_client._request_json.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_member_count_invalid_response():
    """Test handling of invalid API response."""
    # Mock Reddit client with invalid response
    mock_client = AsyncMock()
    mock_client.access_token = "test_token"
    mock_client.user_agent = "test_agent"
    mock_client._request_json = AsyncMock(return_value={"invalid": "response"})
    
    # Test
    member_count = await _fetch_member_count(mock_client, "startups")
    
    # Verify - should return None for invalid response
    assert member_count is None


@pytest.mark.asyncio
async def test_sync_community_members_impl_success(db_session):
    """Test successful sync of community member counts."""
    # Create test communities in database
    communities = [
        CommunityCache(
            community_name="r/startups",
            last_crawled_at=datetime.now(timezone.utc),
            posts_cached=100,
            ttl_seconds=3600,
            is_active=True,
        ),
        CommunityCache(
            community_name="r/entrepreneur",
            last_crawled_at=datetime.now(timezone.utc),
            posts_cached=150,
            ttl_seconds=3600,
            is_active=True,
        ),
    ]
    
    for community in communities:
        db_session.add(community)
    await db_session.commit()
    
    # Mock Reddit client
    with patch("app.tasks.community_member_sync_task.RedditAPIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock _fetch_member_count to return test values
        with patch("app.tasks.community_member_sync_task._fetch_member_count") as mock_fetch:
            mock_fetch.side_effect = [980_000, 1_200_000]
            
            # Run sync
            stats = await _sync_community_members_impl()
    
    # Verify stats
    assert stats["total_communities"] == 2
    assert stats["successful_updates"] == 2
    assert stats["failed_updates"] == 0
    assert stats["skipped_communities"] == 0
    
    # Verify database updates
    result = await db_session.execute(
        select(CommunityCache.community_name, CommunityCache.member_count)
        .where(CommunityCache.community_name.in_(["r/startups", "r/entrepreneur"]))
    )
    counts = {row.community_name: row.member_count for row in result}
    assert counts["r/startups"] == 1_200_000
    assert counts["r/entrepreneur"] == 980_000


@pytest.mark.asyncio
async def test_sync_community_members_impl_with_failures(db_session):
    """Test sync with some failures."""
    # Create test community
    community = CommunityCache(
        community_name="r/startups",
        last_crawled_at=datetime.now(timezone.utc),
        posts_cached=100,
        ttl_seconds=3600,
        is_active=True,
    )
    db_session.add(community)
    await db_session.commit()
    
    # Mock Reddit client
    with patch("app.tasks.community_member_sync_task.RedditAPIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock _fetch_member_count to raise error
        with patch("app.tasks.community_member_sync_task._fetch_member_count") as mock_fetch:
            from app.services.reddit_client import RedditAPIError
            mock_fetch.side_effect = RedditAPIError("API error")
            
            # Run sync
            stats = await _sync_community_members_impl()
    
    # Verify stats
    assert stats["total_communities"] == 1
    assert stats["successful_updates"] == 0
    assert stats["failed_updates"] == 1
    assert len(stats["errors"]) == 1


@pytest.mark.asyncio
async def test_sync_community_members_impl_skips_inactive(db_session):
    """Test that inactive communities are skipped."""
    # Create inactive community
    community = CommunityCache(
        community_name="r/inactive",
        last_crawled_at=datetime.now(timezone.utc),
        posts_cached=0,
        ttl_seconds=3600,
        is_active=False,  # Inactive
    )
    db_session.add(community)
    await db_session.commit()
    
    # Mock Reddit client
    with patch("app.tasks.community_member_sync_task.RedditAPIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Run sync
        stats = await _sync_community_members_impl()
    
    # Verify - should not process any communities
    assert stats["total_communities"] == 0
    assert stats["successful_updates"] == 0


def test_sync_community_member_counts_celery_task():
    """Test Celery task wrapper."""
    with patch("app.tasks.community_member_sync_task.asyncio.run") as mock_run:
        mock_run.return_value = {
            "total_communities": 2,
            "successful_updates": 2,
            "failed_updates": 0,
        }
        
        # Call Celery task
        result = sync_community_member_counts()
        
        # Verify
        assert result["total_communities"] == 2
        assert result["successful_updates"] == 2
        mock_run.assert_called_once()
