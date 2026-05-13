from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.services.crawl.comments_task_runtime import (
    build_comments_task_runtime_deps,
    run_capture_snapshot_daily,
    run_fetch_and_ingest_post_comments,
    run_label_comments_task,
    run_label_posts_recent_task,
)


class _AsyncSession:
    def __init__(self) -> None:
        self.committed = False
        self.executed: list[tuple[str, dict[str, Any]]] = []

    async def __aenter__(self) -> "_AsyncSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        return None

    async def execute(self, stmt: Any, params: dict[str, Any]) -> None:
        self.executed.append((str(stmt), params))


class _SessionFactory:
    def __init__(self, session: _AsyncSession) -> None:
        self._session = session

    def __call__(self) -> _AsyncSession:
        return self._session


def _build_deps(session: _AsyncSession, **overrides: Any) -> Any:
    return build_comments_task_runtime_deps(
        session_factory=_SessionFactory(session),
        persist_comments=overrides.get("persist_comments", lambda *args, **kwargs: 0),
        ensure_crawler_run=overrides.get("ensure_crawler_run", lambda *args, **kwargs: None),
        ensure_crawler_run_target=overrides.get(
            "ensure_crawler_run_target",
            lambda *args, **kwargs: None,
        ),
        enqueue_execute_target_outbox=overrides.get(
            "enqueue_execute_target_outbox",
            lambda *args, **kwargs: None,
        ),
        reddit_client_cls=overrides.get("reddit_client_cls", object),
        classify_and_label_comments=overrides.get(
            "classify_and_label_comments",
            lambda *args, **kwargs: 0,
        ),
        extract_and_label_entities_for_comments=overrides.get(
            "extract_and_label_entities_for_comments",
            lambda *args, **kwargs: 0,
        ),
        persist_subreddit_snapshot=overrides.get(
            "persist_subreddit_snapshot",
            lambda *args, **kwargs: None,
        ),
        label_posts_recent=overrides.get("label_posts_recent", lambda *args, **kwargs: {}),
        compute_removal_ratio_by_subreddit=overrides.get(
            "compute_removal_ratio_by_subreddit",
            lambda *args, **kwargs: {},
        ),
        to_rules_friendliness_score=overrides.get(
            "to_rules_friendliness_score",
            lambda ratio: ratio,
        ),
    )


async def test_run_label_comments_task_commits_and_returns_counts() -> None:
    session = _AsyncSession()

    async def _classify(_session: Any, ids: list[str]) -> int:
        assert ids == ["c1", "c2"]
        return 2

    async def _extract(_session: Any, ids: list[str]) -> int:
        assert ids == ["c1", "c2"]
        return 1

    deps = _build_deps(
        session,
        classify_and_label_comments=_classify,
        extract_and_label_entities_for_comments=_extract,
    )

    payload = await run_label_comments_task(
        deps=deps,
        reddit_comment_ids=["c1", "c2"],
    )

    assert payload == {"status": "ok", "labeled": 2, "entities": 1}
    assert session.committed is True


async def test_run_fetch_and_ingest_post_comments_enqueues_target() -> None:
    session = _AsyncSession()
    seen: dict[str, Any] = {}

    async def _ensure_run(_session: Any, **kwargs: Any) -> None:
        seen["crawl_run"] = kwargs

    async def _ensure_target(_session: Any, **kwargs: Any) -> None:
        seen["target"] = kwargs

    async def _enqueue(_session: Any, **kwargs: Any) -> None:
        seen["outbox"] = kwargs

    deps = _build_deps(
        session,
        ensure_crawler_run=_ensure_run,
        ensure_crawler_run_target=_ensure_target,
        enqueue_execute_target_outbox=_enqueue,
    )

    payload = await run_fetch_and_ingest_post_comments(
        deps=deps,
        queue="backfill_queue",
        source_post_id="p_1",
        subreddit="r/test",
        mode="smart_shallow",
        limit=50,
        depth=2,
    )

    assert payload["status"] == "ok"
    assert payload["enqueued"] == 1
    assert seen["crawl_run"]["config"]["post_id"] == "p_1"
    assert seen["target"]["plan_kind"] == "backfill_comments"
    assert seen["outbox"]["queue"] == "backfill_queue"
    assert session.committed is True


async def test_run_capture_snapshot_daily_returns_zero_without_subs() -> None:
    session = _AsyncSession()
    deps = _build_deps(
        session,
        reddit_client_cls=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("reddit client should not be created")
        ),
    )

    payload = await run_capture_snapshot_daily(
        deps=deps,
        settings=SimpleNamespace(),
        subreddits_raw="",
    )

    assert payload == {"status": "ok", "snapshots": 0}


async def test_run_label_posts_recent_task_passes_limits() -> None:
    session = _AsyncSession()

    async def _label_posts_recent(_session: Any, *, since_days: int, limit: int) -> dict[str, int]:
        assert since_days == 7
        assert limit == 100
        return {"labeled": 8, "entities": 5}

    deps = _build_deps(session, label_posts_recent=_label_posts_recent)

    payload = await run_label_posts_recent_task(
        deps=deps,
        since_days=7,
        limit=100,
    )

    assert payload == {"status": "ok", "labeled": 8, "entities": 5}
    assert session.committed is True
