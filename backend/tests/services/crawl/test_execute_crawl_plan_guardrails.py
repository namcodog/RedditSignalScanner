from __future__ import annotations

from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crawl.plan_contract import CrawlPlanContract, CrawlPlanLimits


@pytest.mark.asyncio
async def test_execute_crawl_plan_patrol_clamps_posts_limit_and_time_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.crawl import execute_plan as execute_plan_module

    captured: dict[str, Any] = {}

    class DummyCrawler:
        def __init__(self, *_: Any, **__: Any) -> None:
            return None

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
            return {"new_posts": 0, "updated_posts": 0, "duplicates": 0}

    monkeypatch.setattr(execute_plan_module, "IncrementalCrawler", DummyCrawler)

    plan = CrawlPlanContract(
        plan_kind="patrol",
        target_type="subreddit",
        target_value="r/test_guardrails",
        reason="cache_expired",
        limits=CrawlPlanLimits(posts_limit=9999),
        meta={"time_filter": "all", "sort": "top", "hot_cache_ttl_hours": 999999},
    )

    await execute_plan_module.execute_crawl_plan(
        plan=plan,
        session=cast(AsyncSession, None),
        reddit_client=object(),
        crawl_run_id="run",
        community_run_id="community",
    )

    assert captured["limit"] == 100
    assert captured["time_filter"] in {"hour", "day"}
    assert captured["sort"] == "top"

