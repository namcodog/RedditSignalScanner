from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.community_pool_loader import CommunityProfile
from app.tasks import crawler_task


class _FakeRedditClient:
    async def __aenter__(self) -> "_FakeRedditClient":
        return self

    async def __aexit__(self, *_args) -> None:
        return None


class _FakeSessionManager:
    def __init__(self, session: "FakeSession") -> None:
        self._session = session

    async def __aenter__(self) -> "FakeSession":
        return self._session

    async def __aexit__(self, *_args) -> None:
        return None


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def rollback(self) -> None:
        return None


class FakeLoader:
    def __init__(self, _db) -> None:
        self.load_seed_calls = 0

    async def load_seed_communities(self) -> dict[str, int]:
        self.load_seed_calls += 1
        return {"loaded": 200}

    async def load_community_pool(self, *_args, **_kwargs) -> list[CommunityProfile]:
        return [
            CommunityProfile(
                name="r/test",
                tier="high",
                categories=[],
                description_keywords={},
                daily_posts=50,
                avg_comment_length=0,
                quality_score=0.9,
                priority="high",
            )
        ]


class FakeIncrementalCrawler:
    def __init__(self, *_args, **_kwargs) -> None:
        self.calls: list[str] = []

    async def crawl_community_incremental(self, community_name: str, **_kwargs) -> dict[str, object]:
        self.calls.append(community_name)
        return {
            "community": community_name,
            "watermark_updated": True,
            "new_posts": 5,
            "updated_posts": 0,
            "duplicates": 0,
            "duration_seconds": 12.5,
        }


class FakeCrawlMetrics:
    def __init__(self, **kwargs) -> None:
        self.payload = kwargs


class FakeScheduler:
    instances: list["FakeScheduler"] = []

    def __init__(self, session) -> None:
        self.session = session
        self.calculate_calls = 0
        self.apply_calls = 0
        FakeScheduler.instances.append(self)

    async def calculate_assignments(self) -> dict[str, list[str]]:
        self.calculate_calls += 1
        return {"tier1": ["r/test"], "tier2": [], "tier3": [], "no_data": [], "blacklisted": []}

    async def apply_assignments(self, assignments: dict[str, list[str]]) -> None:
        assert "tier1" in assignments
        self.apply_calls += 1


@pytest.mark.asyncio
async def test_incremental_crawl_refreshes_quality_tiers(monkeypatch: pytest.MonkeyPatch) -> None:
    """增量抓取完成后应该调用 TieredScheduler 刷新 quality_tier。"""

    fake_settings = SimpleNamespace(
        reddit_client_id="id",
        reddit_client_secret="secret",
        reddit_user_agent="agent",
        reddit_rate_limit=60,
        reddit_rate_limit_window_seconds=60,
        reddit_request_timeout_seconds=10,
        reddit_max_concurrency=2,
        reddit_cache_ttl_seconds=3600,
    )

    session = FakeSession()

    async def fake_build_client(_settings):
        return _FakeRedditClient()

    monkeypatch.setattr(crawler_task, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(crawler_task, "_build_reddit_client", fake_build_client)
    monkeypatch.setattr(crawler_task, "SessionFactory", lambda: _FakeSessionManager(session))
    monkeypatch.setattr(crawler_task, "CommunityPoolLoader", FakeLoader)
    monkeypatch.setattr(crawler_task, "IncrementalCrawler", FakeIncrementalCrawler)
    monkeypatch.setattr(crawler_task, "_mark_failure_hit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(crawler_task, "CrawlMetrics", FakeCrawlMetrics)
    monkeypatch.setattr(crawler_task, "TieredScheduler", FakeScheduler)

    result = await crawler_task._crawl_seeds_incremental_impl(force_refresh=False)

    assert result["status"] == "completed"
    assert FakeScheduler.instances, "TieredScheduler should be instantiated"
    assert FakeScheduler.instances[0].calculate_calls == 1
    assert FakeScheduler.instances[0].apply_calls == 1
    assert session.commits == 1
    assert session.added, "CrawlMetrics should be persisted"
    metrics_payload = session.added[0].payload
    assert metrics_payload["total_communities"] == 1
    assert metrics_payload["successful_crawls"] == 1
    assert metrics_payload["empty_crawls"] == 0
    assert metrics_payload["failed_crawls"] == 0
    assert metrics_payload["avg_latency_seconds"] == pytest.approx(12.5, rel=1e-3)
