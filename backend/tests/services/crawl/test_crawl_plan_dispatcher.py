from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crawl.backfill_comments_workflow import BackfillCommentsWorkflowDeps
from app.services.crawl.backfill_posts_plan_workflow import BackfillPostsPlanWorkflowDeps
from app.services.crawl.crawl_plan_dispatcher import (
    CrawlPlanDispatchDeps,
    CrawlPlanDispatchInput,
    dispatch_crawl_plan,
)
from app.services.crawl.plan_contract import CrawlPlanContract, CrawlPlanLimits
from app.services.crawl.patrol_workflow import PatrolWorkflowDeps
from app.services.crawl.probe_workflow import ProbeWorkflowDeps
from app.services.crawl.seed_archive_workflow import SeedArchiveWorkflowDeps


def _build_deps(**overrides: Any) -> CrawlPlanDispatchDeps:
    async def _noop_workflow(**_: Any) -> Any:
        return SimpleNamespace(payload={"ok": True})

    return CrawlPlanDispatchDeps(
        execute_patrol=overrides.get("execute_patrol", _noop_workflow),
        execute_backfill_posts=overrides.get("execute_backfill_posts", _noop_workflow),
        execute_seed_archive=overrides.get("execute_seed_archive", _noop_workflow),
        execute_probe=overrides.get("execute_probe", _noop_workflow),
        execute_backfill_comments=overrides.get(
            "execute_backfill_comments",
            _noop_workflow,
        ),
        build_patrol_deps=overrides.get(
            "build_patrol_deps",
            lambda: PatrolWorkflowDeps(crawler_factory=object),
        ),
        build_backfill_posts_deps=overrides.get(
            "build_backfill_posts_deps",
            lambda: BackfillPostsPlanWorkflowDeps(crawler_factory=object),
        ),
        build_seed_archive_deps=overrides.get(
            "build_seed_archive_deps",
            lambda: SeedArchiveWorkflowDeps(crawler_factory=object),
        ),
        build_probe_deps=overrides.get(
            "build_probe_deps",
            lambda: ProbeWorkflowDeps(),
        ),
        build_backfill_comments_deps=overrides.get(
            "build_backfill_comments_deps",
            lambda: BackfillCommentsWorkflowDeps(
                resolve_post_context=lambda *args, **kwargs: None,
                count_existing_comments=lambda *args, **kwargs: 0,
                persist_comments=lambda *args, **kwargs: None,
                classify_comments=lambda *args, **kwargs: None,
                extract_comment_entities=lambda *args, **kwargs: None,
            ),
        ),
    )


@pytest.mark.asyncio
async def test_dispatch_crawl_plan_patrol_delegates_to_patrol_workflow() -> None:
    captured: dict[str, Any] = {}

    async def _fake_patrol(**kwargs: Any) -> Any:
        captured["workflow_input"] = kwargs["workflow_input"]
        return SimpleNamespace(payload={"status": "ok"})

    plan = CrawlPlanContract(
        plan_kind="patrol",
        target_type="subreddit",
        target_value="r/test_guardrails",
        reason="cache_expired",
        limits=CrawlPlanLimits(posts_limit=9999),
        meta={"time_filter": "all", "sort": "top", "hot_cache_ttl_hours": 999999},
    )

    await dispatch_crawl_plan(
        CrawlPlanDispatchInput(
            plan=plan,
            session=cast(AsyncSession, None),
            reddit_client=cast(Any, object()),
            crawl_run_id="run",
            community_run_id="community",
        ),
        _build_deps(execute_patrol=_fake_patrol),
    )

    assert captured["workflow_input"].plan.target_value == "r/test_guardrails"


@pytest.mark.asyncio
async def test_dispatch_crawl_plan_backfill_posts_delegates_to_workflow() -> None:
    captured: dict[str, Any] = {}

    async def _fake_backfill_posts(**kwargs: Any) -> Any:
        captured["workflow_input"] = kwargs["workflow_input"]
        return SimpleNamespace(payload={"status": "ok"})

    plan = CrawlPlanContract(
        plan_kind="backfill_posts",
        target_type="subreddit",
        target_value="r/test_backfill",
        reason="coverage_gap",
        window={
            "since": "2026-01-01T00:00:00+00:00",
            "until": "2026-01-03T00:00:00+00:00",
        },
        limits=CrawlPlanLimits(posts_limit=100),
    )

    payload = await dispatch_crawl_plan(
        CrawlPlanDispatchInput(
            plan=plan,
            session=cast(AsyncSession, None),
            reddit_client=cast(Any, object()),
            crawl_run_id="run",
            community_run_id="community",
        ),
        _build_deps(execute_backfill_posts=_fake_backfill_posts),
    )

    assert payload == {"status": "ok"}
    assert captured["workflow_input"].plan.target_value == "r/test_backfill"


@pytest.mark.asyncio
async def test_dispatch_crawl_plan_backfill_posts_requires_window() -> None:
    with pytest.raises(ValueError, match="window.since and window.until"):
        CrawlPlanContract(
            plan_kind="backfill_posts",
            target_type="subreddit",
            target_value="r/test_backfill",
            reason="coverage_gap",
            limits=CrawlPlanLimits(posts_limit=100),
        )


@pytest.mark.asyncio
async def test_dispatch_crawl_plan_probe_delegates_to_probe_workflow() -> None:
    captured: dict[str, Any] = {}

    async def _fake_probe(**kwargs: Any) -> Any:
        captured["workflow_input"] = kwargs["workflow_input"]
        return SimpleNamespace(payload={"status": "ok"})

    plan = CrawlPlanContract(
        plan_kind="probe",
        target_type="query",
        target_value="query:test_probe",
        reason="probe",
        limits=CrawlPlanLimits(posts_limit=10),
        meta={"source": "search"},
    )

    payload = await dispatch_crawl_plan(
        CrawlPlanDispatchInput(
            plan=plan,
            session=cast(AsyncSession, None),
            reddit_client=cast(Any, object()),
            crawl_run_id="run",
            community_run_id="community",
        ),
        _build_deps(execute_probe=_fake_probe),
    )

    assert payload == {"status": "ok"}
    assert captured["workflow_input"].plan.target_value == "query:test_probe"
