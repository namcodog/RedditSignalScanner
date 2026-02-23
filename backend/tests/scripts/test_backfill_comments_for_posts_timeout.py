from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Iterable, List

import pytest

from backend.scripts import backfill_comments_for_posts as mod


class _DummyResult:
    def __init__(self, rows: List[tuple[str, str]]) -> None:
        self._rows = rows

    def fetchall(self) -> List[tuple[str, str]]:
        return self._rows


class _DummySession:
    def __init__(self) -> None:
        self.execute_calls = 0
        self.rollback_calls = 0
        self.commit_calls = 0

    async def execute(self, _stmt: Any, _params: Any | None = None) -> _DummyResult:
        # 第一次返回一条帖子记录，第二次开始返回空集，避免无限循环
        self.execute_calls += 1
        if self.execute_calls == 1:
            return _DummyResult([("t3_dummy", "r/testsub")])
        return _DummyResult([])

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        self.rollback_calls += 1


class _DummySessionCM:
    def __init__(self, session: _DummySession) -> None:
        self._session = session

    async def __aenter__(self) -> _DummySession:
        return self._session

    async def __aexit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        return None


class _DummyRedditClient:
    async def fetch_post_comments(self, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        # 返回一条虚拟评论，触发后续持久化逻辑，再由 asyncio.wait_for 模拟超时
        return [{"id": "t1_dummy", "body": "test"}]

    async def __aenter__(self) -> "_DummyRedditClient":
        return self

    async def __aexit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        return None


@dataclass
class _DummySettings:
    reddit_client_id: str = "id"
    reddit_client_secret: str = "secret"
    reddit_user_agent: str = "ua"
    reddit_rate_limit: int = 10
    reddit_rate_limit_window_seconds: float = 60.0
    reddit_request_timeout_seconds: float = 20.0
    reddit_max_concurrency: int = 1
    reddit_cache_redis_url: str = "redis://localhost:6379/0"


@pytest.mark.asyncio
async def test_backfill_timeout_rolls_back_transaction(monkeypatch: Any) -> None:
    """
    出现 Timeout while processing post 时应主动 rollback，
    避免连接停留在 aborted 状态导致后续请求报
    “Can't reconnect until invalid transaction is rolled back”。
    """

    session = _DummySession()

    def _fake_session_factory() -> _DummySessionCM:
        return _DummySessionCM(session)

    async def _raise_timeout(*_args: Any, **_kwargs: Any) -> None:
        # 模拟 asyncio.wait_for 的超时行为：直接抛出 TimeoutError，
        # 让 backfill 逻辑走到超时分支。
        raise asyncio.TimeoutError()

    def _dummy_reddit_client(*_args: Any, **_kwargs: Any) -> _DummyRedditClient:
        return _DummyRedditClient()

    dummy_settings = _DummySettings()

    monkeypatch.setattr(mod, "SessionFactory", _fake_session_factory)
    monkeypatch.setattr(mod, "RedditAPIClient", _dummy_reddit_client)
    monkeypatch.setattr(mod, "get_settings", lambda: dummy_settings)

    # 只在当前模块作用域内 monkeypatch asyncio.wait_for，
    # 让 _run 中的持久化逻辑走到 Timeout 分支。
    import asyncio as real_asyncio
    monkeypatch.setattr(real_asyncio, "wait_for", _raise_timeout)

    # 触发一次包含超时的回填流程
    result = await mod._run(
        subreddits=["r/testsub"],
        since_days=None,
        page_size=1,
        commit_interval=1,
        skip_labeling=True,
        limit_per_post=10,
        mode="full",
        skip_existing_check=True,
        use_global_limiter=False,
    )

    # 保证流程结束并返回统计结果
    assert "processed_posts" in result
    assert "processed_comments" in result
    # 核心断言：出现超时时必须进行一次 rollback
    assert session.rollback_calls >= 1
