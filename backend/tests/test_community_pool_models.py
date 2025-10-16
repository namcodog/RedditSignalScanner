"""Unit tests for community pool models and schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import uuid4

import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PACKAGE_ROOT = (PROJECT_ROOT / "backend").resolve()
if str(BACKEND_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_PACKAGE_ROOT))

from app.models.community_cache import CommunityCache  # noqa: E402
from app.models.community_pool import (  # noqa: E402
    CommunityPool,
    PendingCommunity,
    CommunityImportHistory,
)
from app.schemas.community_pool import (  # noqa: E402
    PendingCommunityCreate,
    PendingCommunityUpdate,
    PendingCommunityResponse,
    CommunityPoolStats,
    CommunityDiscoveryRequest,
    WarmupMetrics,
)


# ============================================================
# Model Tests
# ============================================================


def test_community_cache_model_creation() -> None:
    """Test CommunityCache model can be instantiated with new fields."""
    cache = CommunityCache(
        community_name="artificial",
        last_crawled_at=datetime.now(timezone.utc),
        posts_cached=100,
        ttl_seconds=3600,
        quality_score=0.85,
        hit_count=50,
        crawl_priority=75,
        crawl_frequency_hours=2,
        is_active=True,
    )
    
    assert cache.community_name == "artificial"
    assert cache.crawl_frequency_hours == 2
    assert cache.is_active is True
    assert cache.crawl_priority == 75


def test_community_cache_default_values() -> None:
    """Test CommunityCache model has correct field types."""
    cache = CommunityCache(
        community_name="startups",
        last_crawled_at=datetime.now(timezone.utc),
        posts_cached=0,
        ttl_seconds=3600,
        quality_score=0.50,
        hit_count=0,
        crawl_priority=50,
        crawl_frequency_hours=2,
        is_active=True,
    )

    assert cache.posts_cached == 0
    assert cache.ttl_seconds == 3600
    assert cache.quality_score == 0.50
    assert cache.hit_count == 0
    assert cache.crawl_priority == 50
    assert cache.crawl_frequency_hours == 2
    assert cache.is_active is True


def test_pending_community_model_creation() -> None:
    """Test PendingCommunity model can be instantiated with new fields."""
    task_id = uuid4()
    reviewer_id = uuid4()
    
    pending = PendingCommunity(
        name="machinelearning",
        discovered_from_keywords={"ai": 10, "ml": 8},
        discovered_count=5,
        status="pending",
        discovered_from_task_id=task_id,
        reviewed_by=reviewer_id,
    )
    
    assert pending.name == "machinelearning"
    assert pending.discovered_from_task_id == task_id
    assert pending.reviewed_by == reviewer_id
    assert pending.discovered_count == 5


def test_pending_community_default_values() -> None:
    """Test PendingCommunity model has correct field types."""
    pending = PendingCommunity(
        name="datascience",
        discovered_count=1,
        status="pending",
    )

    assert pending.discovered_count == 1
    assert pending.status == "pending"
    assert pending.discovered_from_task_id is None
    assert pending.reviewed_by is None
    assert pending.admin_reviewed_at is None


def test_community_pool_model_creation() -> None:
    """Test CommunityPool model can be instantiated."""
    pool = CommunityPool(
        name="entrepreneur",
        tier="high",
        categories={"business": 1, "startup": 1},
        description_keywords={"founder": 10, "business": 8},
        daily_posts=150,
        avg_comment_length=120,
        quality_score=0.75,
        priority="high",
        is_active=True,
    )
    
    assert pool.name == "entrepreneur"
    assert pool.tier == "high"
    assert pool.priority == "high"
    assert pool.is_active is True


# ============================================================
# Schema Tests
# ============================================================


def test_pending_community_create_schema_validation() -> None:
    """Test PendingCommunityCreate schema validation."""
    task_id = uuid4()
    
    # Valid creation
    schema = PendingCommunityCreate(
        name="r/artificial",
        discovered_from_keywords={"ai": 10},
        discovered_from_task_id=task_id,
    )
    
    # Should strip 'r/' prefix and lowercase
    assert schema.name == "artificial"
    assert schema.discovered_from_task_id == task_id


def test_pending_community_create_name_validation() -> None:
    """Test community name validation."""
    # Valid names
    valid_names = ["artificial", "machine_learning", "data-science", "r/startups"]
    for name in valid_names:
        schema = PendingCommunityCreate(name=name)
        assert schema.name.replace("_", "").replace("-", "").isalnum()
    
    # Invalid names (special characters)
    with pytest.raises(ValidationError):
        PendingCommunityCreate(name="invalid@name")
    
    # Too short
    with pytest.raises(ValidationError):
        PendingCommunityCreate(name="ab")


def test_pending_community_update_schema_validation() -> None:
    """Test PendingCommunityUpdate schema validation."""
    reviewer_id = uuid4()
    
    # Valid update
    schema = PendingCommunityUpdate(
        status="approved",
        admin_notes="Good quality community",
        reviewed_by=reviewer_id,
    )
    
    assert schema.status == "approved"
    assert schema.reviewed_by == reviewer_id
    
    # Invalid status
    with pytest.raises(ValidationError):
        PendingCommunityUpdate(status="invalid_status")


def test_pending_community_response_schema() -> None:
    """Test PendingCommunityResponse schema."""
    task_id = uuid4()
    reviewer_id = uuid4()
    now = datetime.now(timezone.utc)
    
    response = PendingCommunityResponse.model_validate(
        {
            "id": 1,
            "name": "artificial",
            "discovered_from_keywords": {"ai": 10},
            "discovered_count": 5,
            "first_discovered_at": now,
            "last_discovered_at": now,
            "status": "approved",
            "admin_reviewed_at": now,
            "admin_notes": "Approved",
            "discovered_from_task_id": task_id,
            "reviewed_by": reviewer_id,
        }
    )
    
    assert response.name == "artificial"
    assert response.status == "approved"
    assert response.discovered_count == 5


def test_community_pool_stats_schema() -> None:
    """Test CommunityPoolStats schema."""
    stats = CommunityPoolStats(
        total_communities=250,
        active_communities=240,
        inactive_communities=10,
        pending_discoveries=15,
        approved_discoveries=200,
        rejected_discoveries=35,
        avg_quality_score=0.72,
        cache_coverage=0.92,
    )
    
    assert stats.total_communities == 250
    assert stats.cache_coverage == 0.92
    
    # Cache coverage must be 0-1
    with pytest.raises(ValidationError):
        CommunityPoolStats(
            total_communities=100,
            active_communities=90,
            inactive_communities=10,
            pending_discoveries=5,
            approved_discoveries=80,
            rejected_discoveries=15,
            avg_quality_score=0.5,
            cache_coverage=1.5,  # Invalid: > 1.0
        )


def test_community_discovery_request_schema() -> None:
    """Test CommunityDiscoveryRequest schema."""
    task_id = uuid4()
    
    request = CommunityDiscoveryRequest(
        product_description="AI-powered note-taking app for researchers",
        task_id=task_id,
        max_communities=20,
    )
    
    assert request.task_id == task_id
    assert request.max_communities == 20
    
    # Description too short
    with pytest.raises(ValidationError):
        CommunityDiscoveryRequest(
            product_description="Too short",
            task_id=task_id,
        )
    
    # Max communities out of range
    with pytest.raises(ValidationError):
        CommunityDiscoveryRequest(
            product_description="Valid description here",
            task_id=task_id,
            max_communities=100,  # > 50
        )


def test_warmup_metrics_schema() -> None:
    """Test WarmupMetrics schema."""
    now = datetime.now(timezone.utc)
    
    metrics = WarmupMetrics(
        period_start=now,
        period_end=now,
        total_communities_cached=250,
        total_posts_cached=25000,
        cache_hit_rate=0.92,
        avg_cache_age_hours=6.5,
        total_api_calls=15000,
        avg_api_calls_per_minute=35.5,
        peak_api_calls_per_minute=58,
        total_analyses=180,
        avg_analysis_time_seconds=155.0,
        p95_analysis_time_seconds=180.0,
        system_uptime_percentage=99.8,
    )
    
    assert metrics.cache_hit_rate == 0.92
    assert metrics.peak_api_calls_per_minute == 58
    assert metrics.system_uptime_percentage == 99.8
    
    # Uptime must be 0-100
    with pytest.raises(ValidationError):
        WarmupMetrics(
            period_start=now,
            period_end=now,
            total_communities_cached=100,
            total_posts_cached=10000,
            cache_hit_rate=0.9,
            avg_cache_age_hours=5.0,
            total_api_calls=5000,
            avg_api_calls_per_minute=30.0,
            peak_api_calls_per_minute=50,
            total_analyses=100,
            avg_analysis_time_seconds=120.0,
            p95_analysis_time_seconds=150.0,
            system_uptime_percentage=105.0,  # Invalid: > 100
        )

