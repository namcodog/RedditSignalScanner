from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.community.truth_source_sync_service import (
    TruthSourceSyncResult,
    sync_legacy_truth_for_community,
)


@dataclass(slots=True)
class TruthSourceBatchResult:
    scanned: int
    synced: int
    skipped: int
    dry_run: bool


async def _load_legacy_pairs(
    session: AsyncSession,
    *,
    include_inactive: bool,
    limit:Optional[ int],
    community_names:Optional[ list[str]],
) ->Optional[ list[tuple[CommunityPool, CommunityCache]]]:
    stmt = (
        select(CommunityPool, CommunityCache)
        .outerjoin(
            CommunityCache,
            func.lower(func.regexp_replace(CommunityCache.community_name, "^r/", ""))
            == func.lower(func.regexp_replace(CommunityPool.name, "^r/", "")),
        )
        .order_by(CommunityPool.id.asc())
    )
    if community_names:
        normalized = [name.lower() for name in community_names]
        stmt = stmt.where(func.lower(CommunityPool.name).in_(normalized))
    if not include_inactive:
        stmt = stmt.where(
            CommunityPool.is_active.is_(True),
            CommunityPool.deleted_at.is_(None),
        )
    if limit is not None:
        stmt = stmt.limit(limit)
    rows = await session.execute(stmt)
    return [(pool, cache) for pool, cache in rows.all()]


async def reconcile_legacy_truth_batch(
    session: AsyncSession,
    *,
    include_inactive: bool = False,
    limit:Optional[ int] = None,
    dry_run: bool = False,
    community_names:Optional[ list[str]] = None,
) -> TruthSourceBatchResult:
    pairs = await _load_legacy_pairs(
        session,
        include_inactive=include_inactive,
        limit=limit,
        community_names=community_names,
    )
    synced = 0
    skipped = 0

    for pool, cache in pairs:
        has_categories = bool(getattr(pool, "categories", None))
        has_runtime = cache is not None
        if not has_categories and not has_runtime:
            skipped += 1
            continue
        await sync_legacy_truth_for_community(session, pool=pool, cache=cache)
        synced += 1

    if dry_run:
        await session.rollback()
    else:
        await session.commit()

    return TruthSourceBatchResult(
        scanned=len(pairs),
        synced=synced,
        skipped=skipped,
        dry_run=dry_run,
    )


async def reconcile_single_community_name(
    session: AsyncSession,
    *,
    community_name: str,
    dry_run: bool = False,
) ->Optional[ TruthSourceSyncResult]:
    pool = (
        await session.execute(
            select(CommunityPool).where(
                func.lower(CommunityPool.name) == community_name.lower()
            )
        )
    ).scalar_one_or_none()
    if pool is None:
        return None
    cache = (
        await session.execute(
            select(CommunityCache).where(
                func.lower(CommunityCache.community_name) == pool.name.lower()
            )
        )
    ).scalar_one_or_none()
    result = await sync_legacy_truth_for_community(session, pool=pool, cache=cache)
    if dry_run:
        await session.rollback()
    else:
        await session.commit()
    return result


__all__ = [
    "TruthSourceBatchResult",
    "reconcile_legacy_truth_batch",
    "reconcile_single_community_name",
]
