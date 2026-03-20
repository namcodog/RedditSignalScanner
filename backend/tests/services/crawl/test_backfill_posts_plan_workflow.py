from __future__ import annotations

from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crawl.backfill_posts_plan_workflow import (
    BackfillPostsPlanWorkflowDeps,
    BackfillPostsPlanWorkflowInput,
    execute_backfill_posts_plan_workflow,
)
from app.services.crawl.plan_contract import CrawlPlanContract, CrawlPlanLimits


@pytest.mark.asyncio
async def test_execute_backfill_posts_plan_workflow_passes_window_and_cursor() -> None:
    captured: dict[str, Any] = {}

    class DummyCrawler:
        def __init__(self, *_: Any, **kwargs: Any) -> None:
            captured["crawler_kwargs"] = kwargs

        async def backfill_posts_window(
            self,
            *_: Any,
            since: Any,
            until: Any,
            max_posts: int,
            sort: str,
            after: str | None,
            **__: Any,
        ) -> dict[str, Any]:
            captured["since"] = since
            captured["until"] = until
            captured["max_posts"] = max_posts
            captured["sort"] = sort
            captured["after"] = after
            return {"status": "completed", "total_fetched": 0}

    plan = CrawlPlanContract(
        plan_kind="backfill_posts",
        target_type="subreddit",
        target_value="r/test_backfill",
        reason="coverage_gap",
        window={
            "since": "2026-01-01T00:00:00+00:00",
            "until": "2026-01-03T00:00:00+00:00",
        },
        limits=CrawlPlanLimits(posts_limit=123),
        meta={"sort": "top", "cursor_after": " t3_cursor "},
    )

    result = await execute_backfill_posts_plan_workflow(
        workflow_input=BackfillPostsPlanWorkflowInput(
            plan=plan,
            session=cast(AsyncSession, None),
            reddit_client=cast(Any, object()),
            crawl_run_id="run",
            community_run_id="community",
        ),
        deps=BackfillPostsPlanWorkflowDeps(crawler_factory=DummyCrawler),
    )

    assert result.payload == {"status": "completed", "total_fetched": 0}
    assert captured["max_posts"] == 123
    assert captured["sort"] == "top"
    assert captured["after"] == "t3_cursor"
    assert captured["crawler_kwargs"]["source_track"] == "backfill_posts"
    assert captured["crawler_kwargs"]["refresh_posts_latest_after_write"] is False
