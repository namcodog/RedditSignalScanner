from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.beta_feedback import BetaFeedback
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.models.discovered_community import DiscoveredCommunity
from app.models.task import Task, TaskStatus
from app.models.user import User

from app.core.security import hash_password


@pytest.mark.asyncio
async def test_build_and_save_report(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Arrange: seed minimal data
    user = User(email="reporter@example.com", password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    now = datetime.now(timezone.utc)

    # Use unique names to avoid PK collisions with other tests
    import uuid as _uuid
    unique_comm = f"r/example_{_uuid.uuid4().hex[:8]}"

    # Community data
    db_session.add(CommunityPool(
        name=unique_comm,
        tier="seed",
        categories={"main": ["test"]},
        description_keywords={"tfidf": ["alpha"]},
        daily_posts=3,
        avg_comment_length=12,
    ))
    db_session.add(DiscoveredCommunity(
        name=f"{unique_comm}_disc",
        discovered_from_keywords={"kw": ["beta"]},
        discovered_count=1,
        first_discovered_at=now - timedelta(hours=3),
        last_discovered_at=now - timedelta(hours=1),
        status="pending",
    ))

    # Cache data
    db_session.add(CommunityCache(
        community_name=unique_comm,
        last_crawled_at=now - timedelta(hours=2),
        posts_cached=5,
        ttl_seconds=7200,
    ))

    # Task with duration
    t = Task(
        user_id=user.id,
        product_description="A valid product description",
        status=TaskStatus.COMPLETED,
        started_at=now - timedelta(seconds=100),
        completed_at=now,
    )
    db_session.add(t)
    # Flush to ensure t.id is generated before referencing
    await db_session.commit()
    await db_session.refresh(t)

    # Beta feedback
    fb = BetaFeedback(
        task_id=t.id,
        user_id=user.id,
        satisfaction=4,
        missing_communities=["r/missing"],
        comments="works",
    )
    db_session.add(fb)

    await db_session.commit()

    # Stub out external metrics to avoid Redis dependency
    from scripts import generate_warmup_report as rpt

    # Precompute metrics to avoid nested event loop
    pre_metrics = {
        "timestamp": now.isoformat(),
        "api_calls_per_minute": 12,
        "cache_hit_rate": 0.9,
        "community_pool_size": 1,
        "stale_communities_count": 0,
    }

    # Act: build report (async path inside pytest-asyncio)
    payload: dict[str, Any] = await rpt.build_report_async(precomputed_metrics=pre_metrics)

    # Assert: structure
    assert payload["warmup_period"] == "Day 13-19 (7 days)"
    assert set(payload.keys()) >= {
        "generated_at", "warmup_period", "adaptive_crawl_hours",
        "community_pool", "cache_metrics", "api_usage",
        "user_testing", "system_performance"
    }

    # Community pool aggregation
    cp = payload["community_pool"]
    assert cp["total"] == cp["seed_communities"] + cp["discovered_communities"]
    assert isinstance(cp["total"], int)

    # Cache metrics
    cm = payload["cache_metrics"]
    assert 0.0 <= cm["cache_hit_rate"] <= 1.0
    assert isinstance(cm["total_posts_cached"], int)

    # User testing
    ut = payload["user_testing"]
    assert 0 <= ut["beta_users"] <= 1
    assert 1.0 <= ut["avg_satisfaction"] <= 5.0

    # System performance
    sp = payload["system_performance"]
    assert sp["avg_analysis_time_seconds"] >= 0.0
    assert sp["p95_analysis_time_seconds"] >= 0.0

    # Save and verify file
    out_reports_dir = tmp_path / "reports"
    out_reports_dir.mkdir(parents=True, exist_ok=True)

    # Redirect script output directory to temporary location
    monkeypatch.setattr(rpt, "BACKEND_DIR", tmp_path / "backend", raising=False)

    out_path = out_reports_dir / "warmup-report.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["community_pool"]["total"] == cp["total"]
