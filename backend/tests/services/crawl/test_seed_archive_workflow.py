from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crawl.plan_contract import CrawlPlanContract, CrawlPlanLimits
from app.services.crawl.seed_archive_workflow import (
    SeedArchiveWorkflowDeps,
    SeedArchiveWorkflowInput,
    execute_seed_archive_workflow,
)


def _build_plan(plan_kind: str) -> CrawlPlanContract:
    return CrawlPlanContract(
        plan_kind=plan_kind,
        target_type="subreddit",
        target_value="r/test_archive",
        reason="seed_sampling",
        limits=CrawlPlanLimits(posts_limit=150),
    )


@pytest.mark.asyncio
async def test_seed_archive_workflow_returns_empty_payload_when_no_posts() -> None:
    plan = _build_plan("seed_top_year")

    class DummyRedditClient:
        async def fetch_subreddit_posts(self, *_: Any, **__: Any) -> tuple[list[Any], str | None]:
            return [], None

    class DummyCrawler:
        async def _dual_write(self, *_: Any, **__: Any) -> tuple[int, int, int]:
            raise AssertionError("_dual_write should not be called for empty archive fetch")

    workflow_result = await execute_seed_archive_workflow(
        workflow_input=SeedArchiveWorkflowInput(
            plan=plan,
            session=cast(AsyncSession, None),
            reddit_client=DummyRedditClient(),
            crawl_run_id="run-1",
            community_run_id="community-1",
        ),
        deps=SeedArchiveWorkflowDeps(
            crawler_factory=lambda **_: DummyCrawler(),
            now_provider=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    )

    assert workflow_result.payload["status"] == "completed"
    assert workflow_result.payload["total_fetched"] == 0
    assert workflow_result.payload["new_posts"] == 0
    assert workflow_result.payload["updated_posts"] == 0
    assert workflow_result.payload["duplicates"] == 0
    assert workflow_result.payload["max_seen_created_at"] is None
    assert workflow_result.payload["min_seen_created_at"] is None


@pytest.mark.asyncio
async def test_seed_archive_workflow_uses_top_all_for_seed_top_all() -> None:
    plan = _build_plan("seed_top_all")
    captured: dict[str, Any] = {}

    class DummyRedditClient:
        async def fetch_subreddit_posts(
            self,
            subreddit: str,
            *,
            limit: int,
            time_filter: str,
            sort: str,
            after: str | None,
        ) -> tuple[list[Any], str | None]:
            captured["subreddit"] = subreddit
            captured["limit"] = limit
            captured["time_filter"] = time_filter
            captured["sort"] = sort
            captured["after"] = after
            return [SimpleNamespace(id="p1", created_utc=1700000000)], None

    class DummyCrawler:
        async def _dual_write(self, community_name: str, posts: list[Any], trigger_comments_fetch: bool = False) -> tuple[int, int, int]:
            captured["dual_write_community"] = community_name
            captured["dual_write_count"] = len(posts)
            captured["trigger_comments_fetch"] = trigger_comments_fetch
            return 1, 0, 0

    workflow_result = await execute_seed_archive_workflow(
        workflow_input=SeedArchiveWorkflowInput(
            plan=plan,
            session=cast(AsyncSession, None),
            reddit_client=DummyRedditClient(),
            crawl_run_id="run-1",
            community_run_id="community-1",
        ),
        deps=SeedArchiveWorkflowDeps(
            crawler_factory=lambda **_: DummyCrawler(),
            now_provider=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    )

    assert captured["subreddit"] == "r/test_archive"
    assert captured["time_filter"] == "all"
    assert captured["sort"] == "top"
    assert captured["after"] is None
    assert captured["dual_write_community"] == "r/test_archive"
    assert captured["dual_write_count"] == 1
    assert captured["trigger_comments_fetch"] is True
    assert workflow_result.payload["plan_kind"] == "seed_top_all"
    assert workflow_result.payload["new_posts"] == 1


@pytest.mark.asyncio
async def test_seed_archive_workflow_uses_controversial_year_and_summarises_seen_window() -> None:
    plan = _build_plan("seed_controversial_year")
    captured: dict[str, Any] = {}

    class DummyRedditClient:
        async def fetch_subreddit_posts(
            self,
            _subreddit: str,
            *,
            limit: int,
            time_filter: str,
            sort: str,
            after: str | None,
        ) -> tuple[list[Any], str | None]:
            captured.setdefault("calls", []).append(
                {
                    "limit": limit,
                    "time_filter": time_filter,
                    "sort": sort,
                    "after": after,
                }
            )
            if after is None:
                return [
                    SimpleNamespace(id="p1", created_utc=1700000000),
                    SimpleNamespace(id="p2", created_utc=1700000300),
                ], "cursor-1"
            return [SimpleNamespace(id="p3", created_utc=1699999000)], None

    class DummyCrawler:
        async def _dual_write(self, *_: Any, **__: Any) -> tuple[int, int, int]:
            return 2, 1, 0

    workflow_result = await execute_seed_archive_workflow(
        workflow_input=SeedArchiveWorkflowInput(
            plan=plan,
            session=cast(AsyncSession, None),
            reddit_client=DummyRedditClient(),
            crawl_run_id="run-1",
            community_run_id="community-1",
        ),
        deps=SeedArchiveWorkflowDeps(
            crawler_factory=lambda **_: DummyCrawler(),
            now_provider=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    )

    first_call, second_call = captured["calls"]
    assert first_call["sort"] == "controversial"
    assert first_call["time_filter"] == "year"
    assert first_call["after"] is None
    assert second_call["after"] == "cursor-1"
    assert workflow_result.payload["total_fetched"] == 3
    assert workflow_result.payload["new_posts"] == 2
    assert workflow_result.payload["updated_posts"] == 1
    assert workflow_result.payload["duplicates"] == 0
    assert workflow_result.payload["max_seen_created_at"] == datetime.fromtimestamp(
        1700000300, tz=timezone.utc
    ).isoformat()
    assert workflow_result.payload["min_seen_created_at"] == datetime.fromtimestamp(
        1699999000, tz=timezone.utc
    ).isoformat()
