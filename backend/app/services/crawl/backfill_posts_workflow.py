from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.community.community_cache_service import (
    mark_crawl_attempt,
    update_backfill_cursor,
    update_backfill_floor_if_lower,
    update_incremental_waterline_if_forward,
)
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditPost
from app.utils.subreddit import normalize_subreddit_name


def _unix_to_datetime(unix_timestamp: float | None) -> datetime | None:
    if unix_timestamp is None:
        return None
    return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)


@dataclass(slots=True)
class BackfillPostsWorkflowInput:
    community_name: str
    since: datetime
    until: datetime
    max_posts: int
    sort: str
    after: str | None
    session: AsyncSession
    reddit_client: RedditAPIClient


@dataclass(slots=True)
class BackfillPostsWorkflowDeps:
    now_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    mark_crawl_attempt: Callable[[str, AsyncSession], Awaitable[None]] = (
        lambda community_name, session: mark_crawl_attempt(community_name, session=session)
    )
    update_backfill_cursor: Callable[..., Awaitable[None]] = update_backfill_cursor
    dual_write: Callable[..., Awaitable[tuple[int, int, int]]] | None = None
    update_backfill_floor: Callable[..., Awaitable[None]] = update_backfill_floor_if_lower
    update_incremental_waterline: Callable[..., Awaitable[None]] = (
        update_incremental_waterline_if_forward
    )


@dataclass(slots=True)
class BackfillPostsWorkflowResult:
    payload: dict[str, object]


async def _load_existing_backfill_cursor(
    session: AsyncSession,
    community_name: str,
) -> tuple[str | None, datetime | None]:
    try:
        row = await session.execute(
            text(
                """
                SELECT backfill_cursor, backfill_cursor_created_at
                FROM community_cache
                WHERE community_name = :name
                """
            ),
            {"name": community_name},
        )
        existing = row.first()
        if not existing:
            return None, None
        return existing[0], existing[1]
    except Exception:
        return None, None


def _build_empty_payload(
    *,
    community_name: str,
    since: datetime,
    until: datetime,
    status: str,
    reason: str | None,
    stop_reason: str | None,
    duration_seconds: float,
    api_calls_total: int,
    items_api_returned: int,
    items_after_window: int,
    items_skipped_outside_window_newer: int,
    items_skipped_outside_window_older: int,
    items_skipped_missing_created_at: int,
    pages_processed: int,
    cursor_before: str | None,
    cursor_after: str | None,
    cursor_created_before: datetime | None,
    cursor_created_after: datetime | None,
) -> dict[str, object]:
    return {
        "community": community_name,
        "status": status,
        "reason": reason,
        "stop_reason": stop_reason,
        "metrics_schema_version": 2,
        "plan_kind": "backfill_posts",
        "window_since": since.isoformat(),
        "window_until": until.isoformat(),
        "total_fetched": 0,
        "unique_posts": 0,
        "new_posts": 0,
        "updated_posts": 0,
        "duplicates": 0,
        "api_calls_total": api_calls_total,
        "items_api_returned": items_api_returned,
        "items_after_window": items_after_window,
        "items_skipped_outside_window_newer": items_skipped_outside_window_newer,
        "items_skipped_outside_window_older": items_skipped_outside_window_older,
        "items_skipped_missing_created_at": items_skipped_missing_created_at,
        "items_new": 0,
        "items_updated": 0,
        "items_duplicate": 0,
        "items_written_posts_inserted": 0,
        "items_written_posts_updated": 0,
        "items_written_posts_total": 0,
        "pages_processed": pages_processed,
        "duration_seconds": duration_seconds,
        "max_seen_created_at": None,
        "min_seen_created_at": None,
        "cursor_before": cursor_before,
        "cursor_after": cursor_after,
        "cursor_created_before": (
            cursor_created_before.isoformat() if cursor_created_before is not None else None
        ),
        "cursor_created_after": (
            cursor_created_after.isoformat() if cursor_created_after is not None else None
        ),
    }


async def execute_backfill_posts_workflow(
    *,
    workflow_input: BackfillPostsWorkflowInput,
    deps: BackfillPostsWorkflowDeps,
) -> BackfillPostsWorkflowResult:
    if workflow_input.since.tzinfo is None:
        since = workflow_input.since.replace(tzinfo=timezone.utc)
    else:
        since = workflow_input.since
    if workflow_input.until.tzinfo is None:
        until = workflow_input.until.replace(tzinfo=timezone.utc)
    else:
        until = workflow_input.until
    if since >= until:
        raise ValueError("since must be < until")

    norm = normalize_subreddit_name(workflow_input.community_name)
    planned_max_posts = max(1, int(workflow_input.max_posts))
    max_pages = max(0, int(os.getenv("BACKFILL_MAX_PAGES_PER_RUN", "0")))
    max_seconds = max(0, int(os.getenv("BACKFILL_MAX_SECONDS_PER_RUN", "0")))
    start_time = deps.now_provider()

    posts: list[RedditPost] = []
    cursor_before = workflow_input.after
    cursor_created_before: datetime | None = None
    existing_cursor, existing_created = await _load_existing_backfill_cursor(
        workflow_input.session,
        norm,
    )
    if cursor_before is None:
        cursor_before = existing_cursor
    cursor_created_before = existing_created

    cursor_after = cursor_before
    truncated = False
    truncated_reason: str | None = None
    pages_processed = 0
    api_calls_total = 0
    items_api_returned = 0
    items_after_window = 0
    items_skipped_outside_window_newer = 0
    items_skipped_outside_window_older = 0
    items_skipped_missing_created_at = 0
    last_batch_min_created: datetime | None = None
    stop_reason: str | None = None

    while len(posts) < planned_max_posts:
        batch_limit = min(100, planned_max_posts - len(posts))
        try:
            batch, next_after = await workflow_input.reddit_client.fetch_subreddit_posts(
                norm,
                limit=batch_limit,
                time_filter="all",
                sort=workflow_input.sort,
                after=cursor_after,
            )
        except Exception:
            await deps.mark_crawl_attempt(norm, workflow_input.session)
            raise

        api_calls_total += 1
        if not batch:
            cursor_after = None
            stop_reason = "no_more_pages"
            break

        pages_processed += 1
        items_api_returned += len(batch)
        batch_created = [
            _unix_to_datetime(post.created_utc)
            for post in batch
            if post.created_utc is not None
        ]
        batch_created = [item for item in batch_created if item is not None]
        if batch_created:
            last_batch_min_created = min(batch_created)
            last_batch_max_created = max(batch_created)
            if cursor_created_before is None or last_batch_max_created > cursor_created_before:
                cursor_created_before = last_batch_max_created
            await deps.update_backfill_cursor(
                norm,
                cursor_after=next_after,
                cursor_created_at=last_batch_min_created,
                session=workflow_input.session,
            )

        hit_floor = False
        for post in batch:
            created_at = _unix_to_datetime(post.created_utc)
            if created_at is None:
                items_skipped_missing_created_at += 1
                continue
            if created_at >= until:
                items_skipped_outside_window_newer += 1
                continue
            if created_at < since:
                hit_floor = True
                items_skipped_outside_window_older += 1
                break
            posts.append(post)
            items_after_window += 1
            if len(posts) >= planned_max_posts:
                break

        if len(posts) >= planned_max_posts:
            truncated = bool(next_after)
            truncated_reason = "cursor_remaining" if truncated else None
            cursor_after = next_after if truncated else None
            if truncated_reason:
                stop_reason = truncated_reason
            break
        if max_pages > 0 and pages_processed >= max_pages:
            truncated = bool(next_after)
            truncated_reason = "budget_remaining" if truncated else None
            cursor_after = next_after if truncated else None
            if truncated_reason:
                stop_reason = truncated_reason
            break
        if max_seconds > 0:
            elapsed = (deps.now_provider() - start_time).total_seconds()
            if elapsed >= max_seconds:
                truncated = bool(next_after)
                truncated_reason = "budget_remaining" if truncated else None
                cursor_after = next_after if truncated else None
                if truncated_reason:
                    stop_reason = truncated_reason
                break
        if hit_floor:
            cursor_after = None
            stop_reason = "floor_reached"
            break
        if not next_after:
            cursor_after = None
            stop_reason = "no_more_pages"
            break
        cursor_after = next_after

    duration = (deps.now_provider() - start_time).total_seconds()
    if not posts:
        status = "completed"
        reason = None
        if stop_reason in {"budget_remaining", "cursor_remaining"}:
            status = "partial"
            reason = stop_reason
        return BackfillPostsWorkflowResult(
            payload=_build_empty_payload(
                community_name=norm,
                since=since,
                until=until,
                status=status,
                reason=reason,
                stop_reason=stop_reason,
                duration_seconds=duration,
                api_calls_total=api_calls_total,
                items_api_returned=items_api_returned,
                items_after_window=items_after_window,
                items_skipped_outside_window_newer=items_skipped_outside_window_newer,
                items_skipped_outside_window_older=items_skipped_outside_window_older,
                items_skipped_missing_created_at=items_skipped_missing_created_at,
                pages_processed=pages_processed,
                cursor_before=cursor_before,
                cursor_after=cursor_after,
                cursor_created_before=cursor_created_before,
                cursor_created_after=last_batch_min_created,
            )
        )

    if deps.dual_write is None:
        raise ValueError("dual_write dependency is required when posts survive window")
    new_count, updated_count, dup_count = await deps.dual_write(
        norm,
        posts,
        trigger_comments_fetch=False,
    )

    max_post = max(posts, key=lambda post: post.created_utc)
    min_post = min(posts, key=lambda post: post.created_utc)
    max_seen = _unix_to_datetime(max_post.created_utc)
    min_seen = _unix_to_datetime(min_post.created_utc)
    if max_seen is None or min_seen is None:
        raise ValueError("backfill_posts requires created_utc for all persisted posts")

    await deps.update_backfill_floor(
        norm,
        backfill_floor=min_seen,
        session=workflow_input.session,
    )
    await deps.update_incremental_waterline(
        norm,
        last_seen_post_id=max_post.id,
        last_seen_created_at=max_seen,
        session=workflow_input.session,
    )
    await workflow_input.session.commit()

    hit_posts_limit = len(posts) >= planned_max_posts
    return BackfillPostsWorkflowResult(
        payload={
            "community": norm,
            "status": "partial" if truncated else "completed",
            "reason": truncated_reason if truncated else None,
            "stop_reason": truncated_reason or stop_reason,
            "metrics_schema_version": 2,
            "plan_kind": "backfill_posts",
            "window_since": since.isoformat(),
            "window_until": until.isoformat(),
            "total_fetched": len(posts),
            "unique_posts": len(posts),
            "new_posts": new_count,
            "updated_posts": updated_count,
            "duplicates": dup_count,
            "api_calls_total": api_calls_total,
            "items_api_returned": items_api_returned,
            "items_after_window": items_after_window,
            "items_skipped_outside_window_newer": items_skipped_outside_window_newer,
            "items_skipped_outside_window_older": items_skipped_outside_window_older,
            "items_skipped_missing_created_at": items_skipped_missing_created_at,
            "items_new": new_count,
            "items_updated": updated_count,
            "items_duplicate": dup_count,
            "items_written_posts_inserted": new_count,
            "items_written_posts_updated": updated_count,
            "items_written_posts_total": new_count + updated_count,
            "pages_processed": pages_processed,
            "hit_posts_limit": hit_posts_limit,
            "duration_seconds": duration,
            "max_seen_created_at": max_seen.isoformat(),
            "min_seen_created_at": min_seen.isoformat(),
            "cursor_after": cursor_after,
            "cursor_before": cursor_before,
            "cursor_created_before": (
                cursor_created_before.isoformat() if cursor_created_before is not None else None
            ),
            "cursor_created_after": (
                last_batch_min_created.isoformat() if last_batch_min_created is not None else None
            ),
        }
    )


__all__ = [
    "BackfillPostsWorkflowDeps",
    "BackfillPostsWorkflowInput",
    "BackfillPostsWorkflowResult",
    "execute_backfill_posts_workflow",
]
