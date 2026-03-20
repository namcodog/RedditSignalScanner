from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crawl.incremental_cache_status_service import (
    EmptyAttemptInput,
    FailureAttemptInput,
    IncrementalCacheStatusDeps,
    WatermarkUpdateInput,
    record_incremental_empty_attempt,
    record_incremental_failure_attempt,
    update_incremental_watermark,
)
from app.services.crawl.incremental_followup_dispatch_service import (
    CommentBackfillDispatchInput,
    IncrementalFollowupDispatchDeps,
    IncrementalScoreRefreshInput,
    dispatch_incremental_score_refresh,
    enqueue_comment_backfill,
    schedule_posts_latest_refresh,
)
from app.services.infrastructure.reddit_client import RedditPost


@dataclass(slots=True)
class IncrementalRuntimeDeps:
    ensure_author: Callable[[str | None, str | None], Awaitable[None]]
    record_failure_attempt: Callable[[str, datetime], Awaitable[None]]
    record_empty_attempt: Callable[[str, datetime], Awaitable[None]]
    dispatch_score_refresh: Callable[[int], Awaitable[None]]
    enqueue_comment_backfill: Callable[[str, list[RedditPost]], None]
    schedule_posts_latest_refresh: Callable[[], None]
    update_watermark: Callable[..., Awaitable[None]]


@dataclass(slots=True)
class IncrementalRuntimeDepsFactoryInput:
    db: AsyncSession
    send_task: Callable[..., object]
    comments_backfill_enabled: bool
    comments_backfill_max_posts: int
    comments_backfill_mode: str
    comments_backfill_limit: int
    comments_backfill_depth: int


def build_incremental_runtime_deps(
    factory_input: IncrementalRuntimeDepsFactoryInput,
) -> IncrementalRuntimeDeps:
    async def _ensure_author(author_id: str | None, author_name: str | None) -> None:
        if not author_id:
            return
        await factory_input.db.execute(
            text(
                """
                INSERT INTO authors (author_id, author_name, created_utc, first_seen_at_global)
                VALUES (:aid, :aname, NOW(), NOW())
                ON CONFLICT (author_id) DO NOTHING
                """
            ),
            {"aid": author_id, "aname": author_name or author_id},
        )

    async def _record_failure_attempt(community_name: str, now: datetime) -> None:
        await record_incremental_failure_attempt(
            FailureAttemptInput(community_name=community_name, now=now),
            IncrementalCacheStatusDeps(db=factory_input.db),
        )

    async def _record_empty_attempt(community_name: str, now: datetime) -> None:
        await record_incremental_empty_attempt(
            EmptyAttemptInput(community_name=community_name, now=now),
            IncrementalCacheStatusDeps(db=factory_input.db),
        )

    async def _dispatch_score_refresh(new_count: int) -> None:
        await dispatch_incremental_score_refresh(
            IncrementalScoreRefreshInput(new_count=new_count),
            IncrementalFollowupDispatchDeps(send_task=factory_input.send_task),
        )

    def _enqueue_comment_backfill(community_name: str, posts: list[RedditPost]) -> None:
        enqueue_comment_backfill(
            CommentBackfillDispatchInput(
                community_name=community_name,
                posts=posts,
                enabled=factory_input.comments_backfill_enabled,
                max_posts=factory_input.comments_backfill_max_posts,
                mode=factory_input.comments_backfill_mode,
                limit=factory_input.comments_backfill_limit,
                depth=factory_input.comments_backfill_depth,
            ),
            IncrementalFollowupDispatchDeps(send_task=factory_input.send_task),
        )

    def _schedule_posts_latest_refresh() -> None:
        schedule_posts_latest_refresh(
            IncrementalFollowupDispatchDeps(send_task=factory_input.send_task)
        )

    async def _update_watermark(
        community_name: str,
        last_seen_post_id: str,
        last_seen_created_at: datetime,
        total_fetched: int,
        new_valid_posts: int,
        dedup_rate: float,
    ) -> None:
        await update_incremental_watermark(
            WatermarkUpdateInput(
                community_name=community_name,
                last_seen_post_id=last_seen_post_id,
                last_seen_created_at=last_seen_created_at,
                total_fetched=total_fetched,
                new_valid_posts=new_valid_posts,
                dedup_rate=dedup_rate,
            ),
            IncrementalCacheStatusDeps(db=factory_input.db),
        )

    return IncrementalRuntimeDeps(
        ensure_author=_ensure_author,
        record_failure_attempt=_record_failure_attempt,
        record_empty_attempt=_record_empty_attempt,
        dispatch_score_refresh=_dispatch_score_refresh,
        enqueue_comment_backfill=_enqueue_comment_backfill,
        schedule_posts_latest_refresh=_schedule_posts_latest_refresh,
        update_watermark=_update_watermark,
    )


__all__ = [
    "IncrementalRuntimeDeps",
    "IncrementalRuntimeDepsFactoryInput",
    "build_incremental_runtime_deps",
]
