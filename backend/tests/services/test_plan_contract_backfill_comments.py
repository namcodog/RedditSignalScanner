from __future__ import annotations

import pytest

from app.services.crawl.plan_contract import CrawlPlanContract, CrawlPlanLimits


def test_backfill_comments_contract_requires_post_ids_and_comments_limit() -> None:
    CrawlPlanContract(
        plan_kind="backfill_comments",
        target_type="post_ids",
        target_value="post_123",
        reason="manual_backfill",
        limits=CrawlPlanLimits(comments_limit=50),
        meta={"subreddit": "r/test"},
    )

    with pytest.raises(Exception):
        CrawlPlanContract(
            plan_kind="backfill_comments",
            target_type="subreddit",
            target_value="r/test",
            reason="bad",
            limits=CrawlPlanLimits(comments_limit=50),
            meta={"subreddit": "r/test"},
        )

    with pytest.raises(Exception):
        CrawlPlanContract(
            plan_kind="backfill_comments",
            target_type="post_ids",
            target_value="post_123",
            reason="bad",
            limits=CrawlPlanLimits(comments_limit=0),
            meta={"subreddit": "r/test"},
        )

