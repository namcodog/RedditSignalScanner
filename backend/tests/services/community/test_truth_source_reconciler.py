from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.community.truth_source_reconciler import (
    normalize_community_name,
    reconcile_legacy_truth,
)


def test_normalize_community_name_requires_value() -> None:
    with pytest.raises(ValueError):
        normalize_community_name("")


def test_reconcile_legacy_truth_builds_new_truth_payloads() -> None:
    pool = CommunityPool(
        id=12,
        name="r/parenting",
        tier="core",
        categories={"categories": ["Family_Parenting", "Home_Lifestyle"]},
        description_keywords={"keywords": ["sleep", "feeding"]},
        daily_posts=6,
        avg_comment_length=120,
        quality_score=Decimal("0.82"),
        priority="high",
        is_active=True,
        is_blacklisted=False,
        health_status="healthy",
    )
    cache = CommunityCache(
        community_name="r/parenting",
        last_crawled_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
        posts_cached=30,
        ttl_seconds=3600,
        quality_score=Decimal("0.77"),
        hit_count=5,
        crawl_priority=60,
        is_active=True,
        backfill_status="DONE_12M",
        sample_posts=22,
        sample_comments=31,
        member_count=120000,
    )
    cache.last_seen_created_at = datetime(2026, 3, 26, tzinfo=timezone.utc)

    reconciled = reconcile_legacy_truth(pool=pool, cache=cache)

    assert reconciled.registry["community_name"] == "r/parenting"
    assert reconciled.registry["legacy_pool_id"] == 12
    assert len(reconciled.memberships) == 2
    assert reconciled.memberships[0]["domain_key"] == "Family_Parenting"
    assert reconciled.memberships[0]["is_primary"] is True
    assert reconciled.governance[0]["decision"] == "approved"
    assert reconciled.runtime_state is not None
    assert reconciled.runtime_state["crawl_status"] == "active"
    assert reconciled.runtime_state["sample_comments"] == 31


def test_reconcile_legacy_truth_handles_blocked_pool_and_needs_backfill() -> None:
    pool = CommunityPool(
        name="daddit",
        tier="semantic",
        categories={"categories": ["Family_Parenting"]},
        description_keywords={},
        daily_posts=0,
        avg_comment_length=0,
        quality_score=Decimal("0.20"),
        priority="low",
        is_active=False,
        is_blacklisted=True,
        blacklist_reason="noise",
    )
    cache = CommunityCache(
        community_name="r/daddit",
        last_crawled_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
        posts_cached=0,
        ttl_seconds=3600,
        quality_score=Decimal("0.30"),
        hit_count=0,
        crawl_priority=20,
        is_active=True,
        backfill_status="NEEDS",
    )

    reconciled = reconcile_legacy_truth(pool=pool, cache=cache)

    assert reconciled.registry["community_name"] == "r/daddit"
    assert reconciled.governance[0]["decision"] == "blocked"
    assert reconciled.governance[0]["reason_code"] == "legacy_blacklist"
    assert reconciled.runtime_state is not None
    assert reconciled.runtime_state["crawl_status"] == "needs_backfill"
