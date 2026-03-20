from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.crawl import crawler_task_runtime as mod


@pytest.mark.asyncio
async def test_build_single_crawl_workflow_deps_delegates_to_cache_and_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cached: list[tuple[str, int | None]] = []
    upserts: list[tuple[str, int, int]] = []

    class _CacheManager:
        async def set_cached_posts(
            self,
            community_name: str,
            posts,
            ttl_seconds: int | None = None,
        ) -> None:
            cached.append((community_name, ttl_seconds))

    class _RedditClient:
        async def fetch_comprehensive_posts(self, subreddit: str, **kwargs):
            return [("comprehensive", subreddit, kwargs)]

        async def fetch_subreddit_posts(self, subreddit: str, **kwargs):
            return [("subreddit", subreddit, kwargs)]

        async def fetch_post_comments(self, post_id: str, **kwargs):
            return [("comments", post_id, kwargs)]

        async def fetch_subreddit_about(self, subreddit: str):
            return {"subreddit": subreddit}

        async def fetch_subreddit_rules(self, subreddit: str):
            return {"rules": subreddit}

    async def _fake_upsert(community_name: str, posts_cached: int, ttl_seconds: int, quality_score=None):
        upserts.append((community_name, posts_cached, ttl_seconds))

    monkeypatch.setattr(mod, "upsert_community_cache", _fake_upsert)

    deps = mod.build_single_crawl_workflow_deps(
        cache_manager=_CacheManager(),
        reddit_client=_RedditClient(),
        session_factory=lambda: AsyncMock(),
        rollback_with_warning=AsyncMock(),
        log_debug=lambda *_: None,
    )

    await deps.set_cached_posts("r/test", [1, 2], ttl_seconds=30)
    await deps.upsert_community_cache("r/test", 2, 30)
    posts = await deps.fetch_subreddit_posts("test", limit=5, time_filter="week", sort="top")
    comments = await deps.fetch_post_comments("p1", sort="top", depth=1, limit=10, mode="topn")

    assert cached == [("r/test", 30)]
    assert upserts == [("r/test", 2, 30)]
    assert posts[0][0] == "subreddit"
    assert comments[0][0] == "comments"
    assert deps.normalize_subreddit_name("r/Test") == "Test"


@pytest.mark.asyncio
async def test_run_seed_crawl_task_uses_injected_builders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class _Client:
        async def __aenter__(self):
            captured["entered"] = True
            return self

        async def __aexit__(self, *_args):
            captured["exited"] = True
            return None

    async def _fake_build_cache_manager(settings):
        captured["cache_settings"] = settings
        return "cache-manager"

    async def _fake_build_reddit_client(settings):
        captured["client_settings"] = settings
        return _Client()

    async def _fake_run_seed_crawl_workflow(workflow_input, deps):
        captured["workflow_input"] = workflow_input
        captured["deps"] = deps
        return SimpleNamespace(payload={"status": "completed", "communities": []})

    monkeypatch.setattr(mod, "run_seed_crawl_workflow", _fake_run_seed_crawl_workflow)

    settings = SimpleNamespace(
        reddit_cache_redis_url="redis://localhost:6379/0",
        reddit_cache_ttl_seconds=60,
    )
    deps_marker = object()

    result = await mod.run_seed_crawl_task(
        force_refresh=True,
        settings=settings,
        build_cache_manager_func=_fake_build_cache_manager,
        build_reddit_client_func=_fake_build_reddit_client,
        session_factory=lambda: AsyncMock(),
        effective_batch_size=10,
        effective_max_concurrency=2,
        effective_time_filter="month",
        effective_sort="top",
        build_seed_crawl_workflow_deps_func=lambda: deps_marker,
    )

    assert result == {"status": "completed", "communities": []}
    assert captured["cache_settings"] is settings
    assert captured["client_settings"] is settings
    assert captured["workflow_input"].cache_manager == "cache-manager"
    assert captured["deps"] is deps_marker
    assert captured["entered"] is True
    assert captured["exited"] is True


@pytest.mark.asyncio
async def test_run_task_outbox_dispatch_uses_env_and_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class _Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

    async def _fake_dispatch(*args, **kwargs):
        captured["dispatch_kwargs"] = kwargs
        return SimpleNamespace(as_dict=lambda: {"status": "completed", "sent": 3})

    async def _fake_commit(session, context=None):
        captured["commit_session"] = session
        captured["commit_context"] = context
        return True

    monkeypatch.setattr(mod, "dispatch_pending_task_outbox", _fake_dispatch)
    monkeypatch.setenv("TASK_OUTBOX_BATCH_SIZE", "17")
    monkeypatch.setenv("TASK_OUTBOX_MAX_RETRIES", "9")

    result = await mod.run_task_outbox_dispatch(
        session_factory=lambda: _Session(),
        send_task=lambda *_args, **_kwargs: None,
        execute_task_name="tasks.crawler.execute_target",
        comments_backfill_queue="comments",
        backfill_posts_queue="backfill",
        commit_session=_fake_commit,
    )

    assert result == {"status": "completed", "sent": 3}
    assert captured["dispatch_kwargs"]["batch_size"] == 17
    assert captured["dispatch_kwargs"]["max_retries"] == 9
    assert captured["dispatch_kwargs"]["execute_task_name"] == "tasks.crawler.execute_target"
    assert isinstance(captured["commit_session"], _Session)
    assert captured["commit_context"] == "dispatch_task_outbox"
