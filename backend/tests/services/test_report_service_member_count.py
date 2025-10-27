"""Tests for ReportService member count functionality.

Related to: P1-5 (硬编码的社区成员数)
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.services.report_service import ReportService, ReportServiceConfig
from app.models.community_cache import CommunityCache
from app.repositories.report_repository import ReportRepository


@pytest.mark.asyncio
async def test_get_community_member_count_from_db(db_session):
    """Test getting member count from database."""
    # Create community with member count in database
    community = CommunityCache(
        community_name="r/startups",
        last_crawled_at=datetime.now(timezone.utc),
        posts_cached=100,
        ttl_seconds=3600,
        is_active=True,
        member_count=1_200_000,  # Set member count
    )
    db_session.add(community)
    await db_session.commit()
    
    # Create ReportService
    config = ReportServiceConfig(
        community_members={"r/other": 500_000},  # Different community in config
        cache_ttl_seconds=3600,
        target_analysis_version="1.0",
    )
    repository = ReportRepository(db_session)
    service = ReportService(db_session, config=config, repository=repository)
    
    # Test
    member_count = await service._get_community_member_count("r/startups")
    
    # Verify - should use DB value, not config
    assert member_count == 1_200_000


@pytest.mark.asyncio
async def test_get_community_member_count_fallback_to_config(db_session):
    """Test fallback to config when DB has no member count."""
    # Create community WITHOUT member count in database
    community = CommunityCache(
        community_name="r/startups",
        last_crawled_at=datetime.now(timezone.utc),
        posts_cached=100,
        ttl_seconds=3600,
        is_active=True,
        member_count=None,  # No member count
    )
    db_session.add(community)
    await db_session.commit()
    
    # Create ReportService with config
    config = ReportServiceConfig(
        community_members={"r/startups": 1_500_000},  # Config value
        cache_ttl_seconds=3600,
        target_analysis_version="1.0",
    )
    repository = ReportRepository(db_session)
    service = ReportService(db_session, config=config, repository=repository)
    
    # Test
    member_count = await service._get_community_member_count("r/startups")
    
    # Verify - should use config value
    assert member_count == 1_500_000


@pytest.mark.asyncio
async def test_get_community_member_count_fallback_to_default(db_session):
    """Test fallback to default when neither DB nor config has value."""
    # No community in database
    
    # Create ReportService without config for this community
    config = ReportServiceConfig(
        community_members={},  # Empty config
        cache_ttl_seconds=3600,
        target_analysis_version="1.0",
    )
    repository = ReportRepository(db_session)
    service = ReportService(db_session, config=config, repository=repository)
    
    # Test
    member_count = await service._get_community_member_count("r/unknown")
    
    # Verify - should use default value
    assert member_count == 100_000


@pytest.mark.asyncio
async def test_get_community_member_count_db_priority(db_session):
    """Test that DB value takes priority over config."""
    # Create community with member count in database
    community = CommunityCache(
        community_name="r/startups",
        last_crawled_at=datetime.now(timezone.utc),
        posts_cached=100,
        ttl_seconds=3600,
        is_active=True,
        member_count=1_200_000,  # DB value
    )
    db_session.add(community)
    await db_session.commit()
    
    # Create ReportService with DIFFERENT config value
    config = ReportServiceConfig(
        community_members={"r/startups": 999_999},  # Different config value
        cache_ttl_seconds=3600,
        target_analysis_version="1.0",
    )
    repository = ReportRepository(db_session)
    service = ReportService(db_session, config=config, repository=repository)
    
    # Test
    member_count = await service._get_community_member_count("r/startups")
    
    # Verify - should use DB value, NOT config
    assert member_count == 1_200_000


@pytest.mark.asyncio
async def test_get_community_member_count_handles_db_error(db_session):
    """Test graceful handling of database errors."""
    # Create ReportService with config
    config = ReportServiceConfig(
        community_members={"r/startups": 1_500_000},
        cache_ttl_seconds=3600,
        target_analysis_version="1.0",
    )
    
    # Mock repository to raise error
    mock_repository = MagicMock()
    mock_repository._db = MagicMock()
    mock_repository._db.execute = AsyncMock(side_effect=Exception("DB error"))
    
    service = ReportService(db_session, config=config, repository=mock_repository)
    
    # Test - should not raise, should fallback to config
    member_count = await service._get_community_member_count("r/startups")
    
    # Verify - should fallback to config value
    assert member_count == 1_500_000


@pytest.mark.asyncio
async def test_get_community_member_count_ignores_zero(db_session):
    """Test that zero member count is treated as missing data."""
    # Create community with zero member count
    community = CommunityCache(
        community_name="r/startups",
        last_crawled_at=datetime.now(timezone.utc),
        posts_cached=100,
        ttl_seconds=3600,
        is_active=True,
        member_count=0,  # Zero (invalid)
    )
    db_session.add(community)
    await db_session.commit()
    
    # Create ReportService with config
    config = ReportServiceConfig(
        community_members={"r/startups": 1_500_000},
        cache_ttl_seconds=3600,
        target_analysis_version="1.0",
    )
    repository = ReportRepository(db_session)
    service = ReportService(db_session, config=config, repository=repository)
    
    # Test
    member_count = await service._get_community_member_count("r/startups")
    
    # Verify - should fallback to config (zero is treated as missing)
    assert member_count == 1_500_000


@pytest.mark.asyncio
async def test_build_overview_uses_db_member_counts(db_session):
    """Test that _build_overview uses member counts from database."""
    from app.schemas.analysis import CommunitySourceDetail
    from app.schemas.report_payload import ReportStats
    
    # Create communities with member counts
    communities_db = [
        CommunityCache(
            community_name="r/startups",
            last_crawled_at=datetime.now(timezone.utc),
            posts_cached=100,
            ttl_seconds=3600,
            is_active=True,
            member_count=1_200_000,
        ),
        CommunityCache(
            community_name="r/entrepreneur",
            last_crawled_at=datetime.now(timezone.utc),
            posts_cached=150,
            ttl_seconds=3600,
            is_active=True,
            member_count=980_000,
        ),
    ]
    for community in communities_db:
        db_session.add(community)
    await db_session.commit()
    
    # Create ReportService
    config = ReportServiceConfig(
        community_members={},  # Empty config to ensure DB is used
        cache_ttl_seconds=3600,
        target_analysis_version="1.0",
    )
    repository = ReportRepository(db_session)
    service = ReportService(db_session, config=config, repository=repository)
    
    # Create test data
    communities_detail = [
        CommunitySourceDetail(
            name="r/startups",
            mentions=50,
            cache_hit_rate=0.9,
            categories=["business"],
            daily_posts=100,
            avg_comment_length=200,
            from_cache=True,
        ),
        CommunitySourceDetail(
            name="r/entrepreneur",
            mentions=30,
            cache_hit_rate=0.8,
            categories=["business"],
            daily_posts=80,
            avg_comment_length=150,
            from_cache=True,
        ),
    ]
    
    stats = ReportStats(
        total_mentions=80,
        positive_mentions=50,
        negative_mentions=20,
        neutral_mentions=10,
    )
    
    # Test
    overview = await service._build_overview(communities_detail, stats)
    
    # Verify member counts from DB
    assert len(overview.top_communities) == 2
    assert overview.top_communities[0].name == "r/startups"
    assert overview.top_communities[0].members == 1_200_000  # From DB
    assert overview.top_communities[1].name == "r/entrepreneur"
    assert overview.top_communities[1].members == 980_000  # From DB

