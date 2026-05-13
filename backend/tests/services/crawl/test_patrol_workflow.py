from __future__ import annotations

from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crawl.patrol_workflow import (
    PatrolWorkflowDeps,
    PatrolWorkflowInput,
    execute_patrol_workflow,
)
from app.services.crawl.plan_contract import CrawlPlanContract, CrawlPlanLimits


@pytest.mark.asyncio
async def test_execute_patrol_workflow_clamps_posts_limit_and_time_filter() -> None:
    captured: dict[str, Any] = {}

    class DummyCrawler:
        def __init__(self, *_: Any, **kwargs: Any) -> None:
            captured["crawler_kwargs"] = kwargs

        async def crawl_community_incremental(
            self,
            *_: Any,
            limit: int,
            time_filter: str,
            sort: str,
            **__: Any,
        ) -> dict[str, Any]:
            captured["limit"] = limit
            captured["time_filter"] = time_filter
            captured["sort"] = sort
            return {"status": "completed", "new_posts": 0}

    plan = CrawlPlanContract(
        plan_kind="patrol",
        target_type="subreddit",
        target_value="r/test_patrol",
        reason="cache_expired",
        limits=CrawlPlanLimits(posts_limit=9999),
        meta={"time_filter": "all", "sort": "top", "hot_cache_ttl_hours": 999999},
    )

    result = await execute_patrol_workflow(
        workflow_input=PatrolWorkflowInput(
            plan=plan,
            session=cast(AsyncSession, None),
            reddit_client=cast(Any, object()),
            crawl_run_id="run",
            community_run_id="community",
        ),
        deps=PatrolWorkflowDeps(crawler_factory=DummyCrawler),
    )

    assert result.payload == {"status": "completed", "new_posts": 0}
    assert captured["limit"] == 100
    assert captured["time_filter"] == "day"
    assert captured["sort"] == "top"
    assert captured["crawler_kwargs"]["source_track"] == "incremental"

