from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_registry import CommunityRegistry
from app.models.community_runtime_state import CommunityRuntimeState


def _ensure_utc(value:Optional[ datetime]) ->Optional[ datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def load_runtime_state_by_name(
    session: AsyncSession,
    community_name: str,
) ->Optional[ CommunityRuntimeState]:
    row = await session.execute(
        select(CommunityRuntimeState)
        .join(
            CommunityRegistry,
            CommunityRegistry.id == CommunityRuntimeState.community_id,
        )
        .where(CommunityRegistry.community_name == community_name)
    )
    return row.scalar_one_or_none()


async def sync_runtime_last_crawled(
    session: AsyncSession,
    *,
    community_name: str,
    crawled_at: datetime,
) -> None:
    runtime = await load_runtime_state_by_name(session, community_name)
    if runtime is None:
        return
    runtime.last_crawled_at = _ensure_utc(crawled_at)


async def sync_runtime_attempt(
    session: AsyncSession,
    *,
    community_name: str,
    attempted_at: datetime,
) -> None:
    runtime = await load_runtime_state_by_name(session, community_name)
    if runtime is None:
        return
    ts = _ensure_utc(attempted_at)
    if runtime.last_attempt_at is None or runtime.last_attempt_at < ts:
        runtime.last_attempt_at = ts


async def sync_runtime_waterline(
    session: AsyncSession,
    *,
    community_name: str,
    last_seen_post_id: str,
    last_seen_created_at: datetime,
) -> None:
    runtime = await load_runtime_state_by_name(session, community_name)
    if runtime is None:
        return
    ts = _ensure_utc(last_seen_created_at)
    if runtime.last_seen_post_at is not None and runtime.last_seen_post_at >= ts:
        return
    runtime.last_seen_post_at = ts
    notes = dict(runtime.runtime_notes or {})
    notes["last_seen_post_id"] = last_seen_post_id
    runtime.runtime_notes = notes


async def sync_runtime_backfill_floor(
    session: AsyncSession,
    *,
    community_name: str,
    backfill_floor: datetime,
) -> None:
    runtime = await load_runtime_state_by_name(session, community_name)
    if runtime is None:
        return
    floor = _ensure_utc(backfill_floor)
    if runtime.backfill_floor is None or runtime.backfill_floor > floor:
        runtime.backfill_floor = floor


async def sync_runtime_backfill_checkpoint(
    session: AsyncSession,
    *,
    community_name: str,
    status:Optional[ str] = None,
    cursor_after:Optional[ str] = None,
    cursor_created_at:Optional[ datetime] = None,
    sample_posts:Optional[ int] = None,
    sample_comments:Optional[ int] = None,
    coverage_months:Optional[ int] = None,
    backfill_capped:Optional[ bool] = None,
) -> None:
    runtime = await load_runtime_state_by_name(session, community_name)
    if runtime is None:
        return

    if sample_posts is not None:
        runtime.sample_posts = int(sample_posts)
    if sample_comments is not None:
        runtime.sample_comments = int(sample_comments)

    notes = dict(runtime.runtime_notes or {})
    if status is not None:
        notes["backfill_status"] = status
    if cursor_after is not None:
        notes["backfill_cursor"] = cursor_after
    if cursor_created_at is not None:
        notes["backfill_cursor_created_at"] = _ensure_utc(cursor_created_at).isoformat()
    if coverage_months is not None:
        notes["coverage_months"] = int(coverage_months)
    if backfill_capped is not None:
        notes["backfill_capped"] = bool(backfill_capped)
    notes["backfill_updated_at"] = datetime.now(timezone.utc).isoformat()
    runtime.runtime_notes = notes
