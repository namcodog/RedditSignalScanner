from __future__ import annotations

import pytest

from app.services.crawl.plan_contract import CrawlPlanContract, CrawlPlanLimits


def test_plan_contract_allows_seed_top_year() -> None:
    plan = CrawlPlanContract(
        plan_kind="seed_top_year",
        target_type="subreddit",
        target_value="r/test",
        reason="seed_sampling",
        limits=CrawlPlanLimits(posts_limit=100),
    )

    assert plan.plan_kind == "seed_top_year"


def test_plan_contract_seed_requires_subreddit_target() -> None:
    with pytest.raises(ValueError):
        CrawlPlanContract(
            plan_kind="seed_top_year",
            target_type="query",
            target_value="test",
            reason="seed_sampling",
            limits=CrawlPlanLimits(posts_limit=100),
        )
