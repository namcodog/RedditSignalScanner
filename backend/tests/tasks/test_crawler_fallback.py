from __future__ import annotations

import asyncio
import types
from dataclasses import dataclass
from typing import Any, Dict, List

import pytest


@pytest.mark.asyncio
async def test_crawl_seeds_impl_applies_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """When initial fetch yields empty posts, the runner should retry with fallback.

    We monkeypatch _crawl_single to first return 0 posts, then >0 posts, and
    assert that the final result indicates a fallback was applied.
    """
    # Import target module late to ensure patches bind correctly
    import app.tasks.crawler_task as mod

    # Fake DB session
    class _FakeSession:
        async def __aenter__(self) -> "_FakeSession":
            return self

        async def __aexit__(self, *_: Any) -> None:  # noqa: ANN401
            return None

        async def execute(self, *_args: Any, **_kwargs: Any) -> Any:  # noqa: ANN401
            class _R:
                rowcount = 0

                def scalar_one_or_none(self) -> Any:  # noqa: ANN401
                    return None

            return _R()

        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

        async def connection(self, **_kwargs: Any) -> None:  # noqa: ANN401
            return None

        def add(self, *_args: Any, **_kwargs: Any) -> None:  # noqa: ANN401
            return None

    async def _fake_session_factory() -> Any:
        return _FakeSession()

    class _FakeSessionFactory:
        async def __aenter__(self) -> _FakeSession:
            return _FakeSession()

        async def __aexit__(self, *_: Any) -> None:
            return None

    # Patch SessionFactory to our fake context manager
    monkeypatch.setattr(mod, "SessionFactory", lambda: _FakeSessionFactory())

    # Fake community pool loader to return one high-tier profile
    @dataclass
    class _Profile:
        name: str
        tier: str
        categories: List[str]
        description_keywords: Dict[str, Any]
        daily_posts: int
        avg_comment_length: int
        quality_score: float
        priority: str

    class _FakeLoader:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        async def load_seed_communities(self) -> Dict[str, int]:
            return {"total_in_file": 1, "loaded": 1, "updated": 0, "total_in_db": 1}

        async def load_community_pool(self, *, force_refresh: bool = False) -> List[_Profile]:
            return [
                _Profile(
                    name="r/TestSub", tier="high", categories=[], description_keywords={},
                    daily_posts=0, avg_comment_length=0, quality_score=0.9, priority="high"
                )
            ]

    monkeypatch.setattr(mod, "CommunityPoolLoader", _FakeLoader)

    class _PlanEntry:
        def __init__(self, profile: _Profile) -> None:
            self.profile = profile
            self.status = "active"
            self.crawl_track = "seed"

    class _FakePlanBuilder:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        async def build_plan(self) -> List[_PlanEntry]:
            return [
                _PlanEntry(
                    _Profile(
                        name="r/TestSub",
                        tier="high",
                        categories=[],
                        description_keywords={},
                        daily_posts=0,
                        avg_comment_length=0,
                        quality_score=0.9,
                        priority="high",
                    )
                )
            ]

    monkeypatch.setattr(mod, "CrawlPlanBuilder", _FakePlanBuilder)

    async def _fake_record_seed_crawl_metrics(*_, **__):  # type: ignore[no-untyped-def]
        return types.SimpleNamespace(
            success_count=1,
            failure_count=0,
            empty_count=0,
            total_new=3,
            avg_latency=0.15,
            tier_metrics_payload={"assignments": {"r/TestSub": "high"}},
        )

    monkeypatch.setattr(mod, "record_seed_crawl_metrics", _fake_record_seed_crawl_metrics)

    # Patch builder helpers (we won't hit external services)
    monkeypatch.setattr(mod, "_build_cache_manager", lambda *_: asyncio.sleep(0))
    # reddit client is used only for passing through to _crawl_single; we patch that below
    class _FakeReddit:
        async def __aenter__(self) -> "_FakeReddit":
            return self

        async def __aexit__(self, *_: Any) -> None:  # noqa: ANN401
            return None

    async def _fake_build_reddit_client(*_: Any) -> _FakeReddit:
        return _FakeReddit()

    monkeypatch.setattr(mod, "_build_reddit_client", _fake_build_reddit_client)

    # Patch _crawl_single to simulate empty → non-empty
    calls: List[Dict[str, Any]] = []

    async def _fake_crawl_single(
        community_name: str,
        *,
        settings: Any,
        cache_manager: Any,
        reddit_client: Any,
        post_limit: int,
        time_filter: str | None = None,
        sort: str | None = None,
        hot_cache_ttl_hours: int | None = None,
        tier_name: str | None = None,
    ) -> Dict[str, Any]:
        calls.append({"time_filter": time_filter, "sort": sort, "limit": post_limit})
        # first call returns empty, subsequent returns 3 posts
        if len(calls) == 1:
            return {"community": community_name, "posts_count": 0, "status": "success", "duration_seconds": 0.1}
        return {"community": community_name, "posts_count": 3, "status": "success", "duration_seconds": 0.2}

    monkeypatch.setattr(mod, "_crawl_single", _fake_crawl_single)

    # Run target
    result = await mod._crawl_seeds_impl(force_refresh=False)

    assert result["status"] == "completed"
    assert result["succeeded"] == 1
    communities = result["communities"]
    assert isinstance(communities, list) and len(communities) == 1
    # Ensure we performed at least 2 calls (fallback path)
    assert len(calls) >= 2


@pytest.mark.asyncio
async def test_planner_lock_logs_when_lock_query_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import app.tasks.crawler_task as mod

    class _BrokenSession:
        async def __aenter__(self) -> "_BrokenSession":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

        async def connection(self, **_kwargs: Any) -> None:
            return None

        async def execute(self, *_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("lock backend unavailable")

    class _BrokenSessionFactory:
        async def __aenter__(self) -> _BrokenSession:
            return _BrokenSession()

        async def __aexit__(self, *_: Any) -> None:
            return None

    monkeypatch.setattr(mod, "SessionFactory", lambda: _BrokenSessionFactory())

    with caplog.at_level("WARNING"):
        async with mod._planner_lock("round1-repair") as acquired:
            assert acquired is False

    assert "planner lock acquire failed" in caplog.text
