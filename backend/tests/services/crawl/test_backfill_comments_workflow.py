from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.crawl.backfill_comments_workflow import (
    BackfillCommentsWorkflowDeps,
    BackfillCommentsWorkflowInput,
    execute_backfill_comments_workflow,
)
from app.services.crawl.plan_contract import CrawlPlanContract, CrawlPlanLimits


@pytest.mark.asyncio
async def test_backfill_comments_workflow_maps_internal_post_id() -> None:
    persist_comments = AsyncMock(return_value=1)
    reddit_client = AsyncMock()
    reddit_client.fetch_post_comments.return_value = [{"id": "c1", "body": "ok"}]

    result = await execute_backfill_comments_workflow(
        workflow_input=BackfillCommentsWorkflowInput(
            plan=CrawlPlanContract(
                plan_kind="backfill_comments",
                target_type="post_ids",
                target_value="123",
                reason="manual_backfill_comments",
                limits=CrawlPlanLimits(comments_limit=50),
                meta={"subreddit": "r/testsub"},
            ),
            session=SimpleNamespace(),
            reddit_client=reddit_client,
            crawl_run_id="run",
            community_run_id="community",
        ),
        deps=BackfillCommentsWorkflowDeps(
            resolve_post_context=AsyncMock(
                return_value=("t3_real", "r/testsub", 10, 2, datetime.now(timezone.utc))
            ),
            count_existing_comments=AsyncMock(return_value=0),
            persist_comments=persist_comments,
            classify_comments=AsyncMock(return_value=0),
            extract_comment_entities=AsyncMock(return_value=0),
        ),
    )

    assert result.payload["status"] == "completed"
    reddit_client.fetch_post_comments.assert_awaited_once()
    persist_comments.assert_awaited_once()
    _, kwargs = persist_comments.await_args
    assert kwargs["source_post_id"] == "t3_real"
    assert kwargs["subreddit"] == "r/testsub"


@pytest.mark.asyncio
async def test_backfill_comments_workflow_skips_when_no_comments() -> None:
    reddit_client = AsyncMock()

    result = await execute_backfill_comments_workflow(
        workflow_input=BackfillCommentsWorkflowInput(
            plan=CrawlPlanContract(
                plan_kind="backfill_comments",
                target_type="post_ids",
                target_value="t3_empty",
                reason="manual_backfill_comments",
                limits=CrawlPlanLimits(comments_limit=50),
                meta={"subreddit": "r/testsub"},
            ),
            session=SimpleNamespace(),
            reddit_client=reddit_client,
            crawl_run_id="run",
            community_run_id="community",
        ),
        deps=BackfillCommentsWorkflowDeps(
            resolve_post_context=AsyncMock(
                return_value=("t3_empty", "r/testsub", 0, 0, datetime.now(timezone.utc))
            ),
            count_existing_comments=AsyncMock(return_value=0),
            persist_comments=AsyncMock(return_value=0),
            classify_comments=AsyncMock(return_value=0),
            extract_comment_entities=AsyncMock(return_value=0),
        ),
    )

    assert result.payload == {
        "plan_kind": "backfill_comments",
        "status": "completed",
        "processed": 0,
        "reason": "no_comments",
    }
    reddit_client.fetch_post_comments.assert_not_called()


@pytest.mark.asyncio
async def test_backfill_comments_workflow_old_post_uses_top_only_smart_config() -> None:
    reddit_client = AsyncMock()
    reddit_client.fetch_post_comments.return_value = [{"id": "c1", "body": "ok"}]
    persist_comments = AsyncMock(return_value=1)

    result = await execute_backfill_comments_workflow(
        workflow_input=BackfillCommentsWorkflowInput(
            plan=CrawlPlanContract(
                plan_kind="backfill_comments",
                target_type="post_ids",
                target_value="t3_old",
                reason="manual_backfill_comments",
                limits=CrawlPlanLimits(comments_limit=50),
                meta={"subreddit": "r/testsub"},
            ),
            session=SimpleNamespace(),
            reddit_client=reddit_client,
            crawl_run_id="run",
            community_run_id="community",
        ),
        deps=BackfillCommentsWorkflowDeps(
            resolve_post_context=AsyncMock(
                return_value=(
                    "t3_old",
                    "r/testsub",
                    10,
                    80,
                    datetime.now(timezone.utc) - timedelta(days=10),
                )
            ),
            count_existing_comments=AsyncMock(return_value=0),
            persist_comments=persist_comments,
            classify_comments=AsyncMock(return_value=0),
            extract_comment_entities=AsyncMock(return_value=0),
        ),
    )

    assert result.payload["status"] == "completed"
    _, kwargs = reddit_client.fetch_post_comments.await_args
    assert kwargs["mode"] == "smart_shallow"
    assert kwargs["smart_config"]["smart_top_limit"] == 40
    assert kwargs["smart_config"]["smart_new_limit"] == 0
