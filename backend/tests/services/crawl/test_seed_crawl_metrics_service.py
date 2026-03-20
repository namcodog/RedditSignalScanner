from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from app.services.crawl.seed_crawl_metrics_service import (
    SeedCrawlMetricsDeps,
    SeedCrawlMetricsInput,
    record_seed_crawl_metrics,
)


class _FakeSession:
    def __init__(self) -> None:
        self.executed: list[Any] = []
        self.added: list[Any] = []
        self.commit_calls = 0
        self.rollback_calls = 0

    async def execute(self, stmt: Any) -> None:
        self.executed.append(stmt)

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        self.rollback_calls += 1

    def add(self, obj: Any) -> None:
        self.added.append(obj)


class _FakeSessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, *_args: Any) -> None:
        return None


class _FakeScheduler:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session
        self.applied: dict[str, Any] | None = None

    async def calculate_assignments(self) -> dict[str, Any]:
        return {"r/TestSub": "high"}

    async def apply_assignments(self, assignments: dict[str, Any]) -> None:
        self.applied = assignments


@dataclass
class _FakeMetricsModel:
    __table__ = object()
    metric_date: Any = None
    metric_hour: Any = None
    cache_hit_rate: Any = None
    valid_posts_24h: Any = None
    total_communities: Any = None
    successful_crawls: Any = None
    empty_crawls: Any = None
    failed_crawls: Any = None
    avg_latency_seconds: Any = None
    total_new_posts: Any = None
    total_updated_posts: Any = None
    total_duplicates: Any = None
    tier_assignments: Any = None

    class _Counter:
        def __add__(self, other: Any) -> tuple[str, Any]:
            return ("plus", other)

    successful_crawls = _Counter()
    empty_crawls = _Counter()
    failed_crawls = _Counter()
    total_new_posts = _Counter()
    total_updated_posts = _Counter()
    total_duplicates = _Counter()


def _results() -> list[dict[str, Any]]:
    return [
        {"community": "r/TestSub", "status": "success", "posts_count": 3, "duration_seconds": 0.2},
        {
            "community": "r/SlowSub",
            "status": "success",
            "posts_count": 0,
            "duration_seconds": 0.4,
            "rate_limited": True,
        },
        {"community": "r/BadSub", "status": "failed", "error": "boom"},
    ]


@pytest.mark.asyncio
async def test_record_seed_crawl_metrics_uses_upsert_and_applies_tiers() -> None:
    session = _FakeSession()
    scheduler_holder: dict[str, _FakeScheduler] = {}

    def _scheduler_factory(db: _FakeSession) -> _FakeScheduler:
        scheduler = _FakeScheduler(db)
        scheduler_holder["scheduler"] = scheduler
        return scheduler

    result = await record_seed_crawl_metrics(
        metrics_input=SeedCrawlMetricsInput(
            results=_results(),
            total_profiles=3,
        ),
        deps=SeedCrawlMetricsDeps(
            session_factory=lambda: _FakeSessionFactory(session),
            scheduler_factory=_scheduler_factory,
            crawl_metrics_model=_FakeMetricsModel,
            build_upsert_stmt=lambda **kwargs: {"stmt": kwargs},
            now_factory=lambda: datetime(2026, 3, 16, 10, tzinfo=timezone.utc),
        ),
    )

    assert result.success_count == 2
    assert result.failure_count == 1
    assert result.empty_count == 1
    assert result.total_new == 3
    assert round(result.avg_latency, 2) == 0.30
    assert result.tier_metrics_payload["assignments"] == {"r/TestSub": "high"}
    assert result.tier_metrics_payload["rate_limit_hits"] == 1
    assert result.tier_metrics_payload["downgraded_communities"] == ["r/SlowSub"]
    assert len(session.executed) == 1
    assert session.commit_calls == 1
    assert scheduler_holder["scheduler"].applied == {"r/TestSub": "high"}


@pytest.mark.asyncio
async def test_record_seed_crawl_metrics_falls_back_to_add_when_upsert_fails() -> None:
    session = _FakeSession()

    class _FallbackMetricsModel:
        __table__ = object()

        def __init__(self, **kwargs: Any) -> None:
            self.payload = kwargs

    result = await record_seed_crawl_metrics(
        metrics_input=SeedCrawlMetricsInput(
            results=_results(),
            total_profiles=3,
        ),
        deps=SeedCrawlMetricsDeps(
            session_factory=lambda: _FakeSessionFactory(session),
            scheduler_factory=lambda db: _FakeScheduler(db),
            crawl_metrics_model=_FallbackMetricsModel,
            build_upsert_stmt=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("upsert failed")),
            now_factory=lambda: datetime(2026, 3, 16, 10, tzinfo=timezone.utc),
        ),
    )

    assert result.tier_metrics_payload["assignments"] == {"r/TestSub": "high"}
    assert len(session.added) == 1
    added = session.added[0]
    assert added.payload["successful_crawls"] == 2
    assert added.payload["failed_crawls"] == 1
    assert session.commit_calls == 1
