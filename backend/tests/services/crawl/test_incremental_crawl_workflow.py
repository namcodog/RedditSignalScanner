from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.crawl.incremental_crawl_workflow import (
    IncrementalCrawlWorkflowDeps,
    IncrementalCrawlWorkflowInput,
    run_incremental_crawl_workflow,
)


def _post(post_id: str, created_utc: float) -> SimpleNamespace:
    return SimpleNamespace(id=post_id, created_utc=created_utc)


@pytest.mark.asyncio
async def test_incremental_crawl_workflow_records_empty_metrics() -> None:
    record_empty_attempt = AsyncMock()
    record_crawl_metrics = AsyncMock()
    result = await run_incremental_crawl_workflow(
        workflow_input=IncrementalCrawlWorkflowInput(
            community_name="r/testempty",
            limit=25,
            time_filter="month",
            sort="top",
            start_time=datetime.now(timezone.utc),
        ),
        deps=IncrementalCrawlWorkflowDeps(
            get_watermark=AsyncMock(return_value=None),
            fetch_posts=AsyncMock(return_value=[]),
            filter_spam_posts=lambda _community, posts: posts,
            dual_write=AsyncMock(),
            dispatch_score_refresh=AsyncMock(),
            update_watermark=AsyncMock(),
            record_failure_attempt=AsyncMock(),
            record_empty_attempt=record_empty_attempt,
            record_crawl_metrics=record_crawl_metrics,
        ),
    )

    assert result.payload["watermark_updated"] is False
    record_empty_attempt.assert_awaited_once()
    record_crawl_metrics.assert_awaited_once()


@pytest.mark.asyncio
async def test_incremental_crawl_workflow_records_failure_attempt() -> None:
    record_failure_attempt = AsyncMock()
    result = await run_incremental_crawl_workflow(
        workflow_input=IncrementalCrawlWorkflowInput(
            community_name="r/testfailure",
            limit=25,
            time_filter="month",
            sort="top",
            start_time=datetime.now(timezone.utc),
        ),
        deps=IncrementalCrawlWorkflowDeps(
            get_watermark=AsyncMock(return_value=None),
            fetch_posts=AsyncMock(side_effect=RuntimeError("boom")),
            filter_spam_posts=lambda _community, posts: posts,
            dual_write=AsyncMock(),
            dispatch_score_refresh=AsyncMock(),
            update_watermark=AsyncMock(),
            record_failure_attempt=record_failure_attempt,
            record_empty_attempt=AsyncMock(),
            record_crawl_metrics=AsyncMock(),
        ),
    )

    assert result.payload["error"] == "boom"
    record_failure_attempt.assert_awaited_once()


@pytest.mark.asyncio
async def test_incremental_crawl_workflow_updates_watermark_and_dispatches_score() -> None:
    dispatch_score_refresh = AsyncMock()
    update_watermark = AsyncMock()
    record_crawl_metrics = AsyncMock()
    dual_write = AsyncMock(return_value=(2, 1, 0))
    posts = [_post("p1", 1700000000.0), _post("p2", 1700000100.0)]
    result = await run_incremental_crawl_workflow(
        workflow_input=IncrementalCrawlWorkflowInput(
            community_name="r/testsuccess",
            limit=200,
            time_filter="month",
            sort="top",
            start_time=datetime.now(timezone.utc),
        ),
        deps=IncrementalCrawlWorkflowDeps(
            get_watermark=AsyncMock(return_value=None),
            fetch_posts=AsyncMock(return_value=posts),
            filter_spam_posts=lambda _community, payload: payload,
            dual_write=dual_write,
            dispatch_score_refresh=dispatch_score_refresh,
            update_watermark=update_watermark,
            record_failure_attempt=AsyncMock(),
            record_empty_attempt=AsyncMock(),
            record_crawl_metrics=record_crawl_metrics,
        ),
    )

    assert result.payload["new_posts"] == 2
    dual_write.assert_awaited_once()
    dispatch_score_refresh.assert_awaited_once_with(2)
    update_watermark.assert_awaited_once()
    record_crawl_metrics.assert_awaited_once()
