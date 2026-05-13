from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.crawl.incremental_crawler import IncrementalCrawler
from app.services.crawl.incremental_crawler_runtime import (
    IncrementalCrawlerRuntime,
    IncrementalCrawlerRuntimeInput,
)
from app.services.crawl.incremental_runtime_deps_factory import IncrementalRuntimeDeps


def _build_runtime() -> IncrementalCrawlerRuntime:
    runtime_deps = IncrementalRuntimeDeps(
        ensure_author=AsyncMock(),
        record_failure_attempt=AsyncMock(),
        record_empty_attempt=AsyncMock(),
        dispatch_score_refresh=AsyncMock(),
        enqueue_comment_backfill=MagicMock(),
        schedule_posts_latest_refresh=MagicMock(),
        update_watermark=AsyncMock(),
    )
    return IncrementalCrawlerRuntime(
        IncrementalCrawlerRuntimeInput(
            db=AsyncMock(),
            reddit_client=AsyncMock(),
            runtime_deps=runtime_deps,
            blacklist=None,
            hot_cache_ttl_hours=24,
            refresh_posts_latest_after_write=True,
            source_track="incremental",
            crawl_run_id="crawl-run",
            community_run_id="community-run",
            spam_filter_mode="drop",
            duplicate_mode="drop",
            spam_classifier=None,
            normalize_subreddit_name=lambda value: value,
            unix_to_datetime=lambda ts: datetime.fromtimestamp(ts, tz=timezone.utc),
            text_norm_hash_available=AsyncMock(return_value=True),
            posts_raw_has_crawl_run_id=AsyncMock(return_value=True),
            posts_raw_has_community_run_id=AsyncMock(return_value=True),
            is_current_unique_violation=lambda exc: False,
        )
    )


@pytest.mark.asyncio
async def test_incremental_runtime_builds_incremental_deps_with_comment_backfill() -> None:
    runtime = _build_runtime()
    recorded: dict[str, object] = {}

    async def _fake_dual_write(
        community_name: str,
        posts: list[object],
        *,
        trigger_comments_fetch: bool = False,
    ) -> tuple[int, int, int]:
        recorded["community_name"] = community_name
        recorded["posts"] = posts
        recorded["trigger_comments_fetch"] = trigger_comments_fetch
        return (1, 2, 3)

    runtime.dual_write = _fake_dual_write  # type: ignore[method-assign]

    deps = runtime.build_incremental_workflow_deps()
    result = await deps.dual_write("r/test", [])

    assert result == (1, 2, 3)
    assert recorded["community_name"] == "r/test"
    assert recorded["trigger_comments_fetch"] is True


def test_incremental_crawler_keeps_loaded_blacklist(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel_blacklist = object()
    monkeypatch.setattr(
        "app.services.crawl.incremental_crawler.BlacklistConfig",
        lambda _path: sentinel_blacklist,
    )

    crawler = IncrementalCrawler(db=AsyncMock(), reddit_client=AsyncMock())

    assert crawler.blacklist is sentinel_blacklist
