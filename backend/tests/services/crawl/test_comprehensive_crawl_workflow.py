from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.services.crawl.comprehensive_crawl_workflow import (
    ComprehensiveCrawlWorkflowDeps,
    ComprehensiveCrawlWorkflowInput,
    run_comprehensive_crawl_workflow,
)


def _post(post_id: str, created_at: datetime) -> SimpleNamespace:
    return SimpleNamespace(id=post_id, created_utc=created_at.timestamp())


def _workflow_input(**overrides: Any) -> ComprehensiveCrawlWorkflowInput:
    base = {
        "community_name": "r/test",
        "time_filter": "all",
        "max_per_strategy": 1000,
        "ignore_watermark": True,
        "start_time": datetime.now(timezone.utc) - timedelta(seconds=2),
    }
    base.update(overrides)
    return ComprehensiveCrawlWorkflowInput(**base)


@pytest.mark.asyncio
async def test_comprehensive_crawl_workflow_returns_error_payload_on_fetch_failure() -> None:
    async def _fetch(*_args: Any, **_kwargs: Any) -> list[Any]:
        raise RuntimeError("reddit down")

    async def _get_watermark(_community: str) -> None:
        return None

    async def _noop(*_args: Any, **_kwargs: Any) -> None:
        return None

    async def _dual_write(*_args: Any, **_kwargs: Any) -> tuple[int, int, int]:
        raise AssertionError("dual write should not run")

    result = await run_comprehensive_crawl_workflow(
        workflow_input=_workflow_input(),
        deps=ComprehensiveCrawlWorkflowDeps(
            normalize_subreddit_name=lambda value: value[2:],
            get_watermark=_get_watermark,
            fetch_comprehensive_posts=_fetch,
            unix_to_datetime=lambda ts: datetime.fromtimestamp(ts, tz=timezone.utc),
            filter_spam_posts=lambda _community, posts: list(posts),
            dual_write=_dual_write,
            update_watermark=_noop,  # type: ignore[arg-type]
        ),
    )

    assert result.payload["error"] == "reddit down"
    assert result.payload["total_fetched"] == 0


@pytest.mark.asyncio
async def test_comprehensive_crawl_workflow_filters_by_watermark_and_skips_empty() -> None:
    now = datetime.now(timezone.utc)

    async def _get_watermark(_community: str) -> datetime:
        return now

    async def _fetch(*_args: Any, **_kwargs: Any) -> list[Any]:
        return [_post("old-1", now - timedelta(minutes=1))]

    async def _noop(*_args: Any, **_kwargs: Any) -> None:
        return None

    async def _dual_write(*_args: Any, **_kwargs: Any) -> tuple[int, int, int]:
        raise AssertionError("dual write should not run")

    result = await run_comprehensive_crawl_workflow(
        workflow_input=_workflow_input(ignore_watermark=False),
        deps=ComprehensiveCrawlWorkflowDeps(
            normalize_subreddit_name=lambda value: value[2:],
            get_watermark=_get_watermark,
            fetch_comprehensive_posts=_fetch,
            unix_to_datetime=lambda ts: datetime.fromtimestamp(ts, tz=timezone.utc),
            filter_spam_posts=lambda _community, posts: list(posts),
            dual_write=_dual_write,
            update_watermark=_noop,  # type: ignore[arg-type]
        ),
    )

    assert result.payload["total_fetched"] == 1
    assert result.payload["unique_posts"] == 0
    assert result.payload["new_posts"] == 0


@pytest.mark.asyncio
async def test_comprehensive_crawl_workflow_writes_and_updates_watermark() -> None:
    now = datetime.now(timezone.utc)
    posts = [
        _post("p1", now - timedelta(minutes=2)),
        _post("p2", now - timedelta(minutes=1)),
    ]
    captured: dict[str, Any] = {}

    async def _fetch(*_args: Any, **_kwargs: Any) -> list[Any]:
        return posts

    async def _get_watermark(_community: str) -> None:
        return None

    async def _dual_write(community_name: str, post_batch: Any) -> tuple[int, int, int]:
        captured["community_name"] = community_name
        captured["posts"] = list(post_batch)
        return (1, 1, 0)

    async def _update_watermark(
        community_name: str,
        latest_post_id: str,
        latest_created_at: datetime,
        total_fetched: int,
        new_valid_posts: int,
        dedup_rate: float,
    ) -> None:
        captured["watermark"] = {
            "community_name": community_name,
            "latest_post_id": latest_post_id,
            "latest_created_at": latest_created_at,
            "total_fetched": total_fetched,
            "new_valid_posts": new_valid_posts,
            "dedup_rate": dedup_rate,
        }

    result = await run_comprehensive_crawl_workflow(
        workflow_input=_workflow_input(),
        deps=ComprehensiveCrawlWorkflowDeps(
            normalize_subreddit_name=lambda value: value[2:],
            get_watermark=_get_watermark,
            fetch_comprehensive_posts=_fetch,
            unix_to_datetime=lambda ts: datetime.fromtimestamp(ts, tz=timezone.utc),
            filter_spam_posts=lambda _community, incoming: list(incoming),
            dual_write=_dual_write,
            update_watermark=_update_watermark,
        ),
    )

    assert captured["community_name"] == "r/test"
    assert len(captured["posts"]) == 2
    assert captured["watermark"]["latest_post_id"] == "p2"
    assert captured["watermark"]["total_fetched"] == 2
    assert captured["watermark"]["new_valid_posts"] == 1
    assert result.payload["new_posts"] == 1
    assert result.payload["updated_posts"] == 1
    assert result.payload["duplicates"] == 0
    assert result.payload["unique_posts"] == 2
