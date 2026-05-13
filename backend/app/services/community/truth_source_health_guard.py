from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "TruthSourceHealthSnapshot",
    "assert_restore_truth_health",
    "assert_truth_source_write_safe",
    "read_truth_source_health_snapshot",
]


@dataclass(slots=True)
class TruthSourceHealthSnapshot:
    enabled_registry_count: int
    approved_registry_count: int
    active_runtime_count: int
    active_pool_count: int
    active_cache_count: int


async def read_truth_source_health_snapshot(
    session: AsyncSession,
) -> TruthSourceHealthSnapshot:
    row = (
        await session.execute(
            text(
                """
                WITH approved_registry AS (
                  SELECT DISTINCT m.community_id
                  FROM community_domain_membership m
                  JOIN community_governance_decision g
                    ON g.membership_id = m.id
                  WHERE m.is_current = TRUE
                    AND g.is_current = TRUE
                    AND g.decision = 'approved'
                ),
                active_runtime AS (
                  SELECT DISTINCT community_id
                  FROM community_runtime_state
                  WHERE is_enabled = TRUE
                    AND crawl_status IN ('active', 'needs_backfill')
                )
                SELECT
                  (SELECT COUNT(*) FROM community_registry WHERE is_enabled = TRUE) AS enabled_registry_count,
                  (SELECT COUNT(*) FROM approved_registry) AS approved_registry_count,
                  (SELECT COUNT(*) FROM active_runtime) AS active_runtime_count,
                  (SELECT COUNT(*) FROM community_pool WHERE is_active = TRUE) AS active_pool_count,
                  (SELECT COUNT(*) FROM community_cache WHERE is_active = TRUE) AS active_cache_count
                """
            )
        )
    ).mappings().one()
    return TruthSourceHealthSnapshot(
        enabled_registry_count=int(row["enabled_registry_count"] or 0),
        approved_registry_count=int(row["approved_registry_count"] or 0),
        active_runtime_count=int(row["active_runtime_count"] or 0),
        active_pool_count=int(row["active_pool_count"] or 0),
        active_cache_count=int(row["active_cache_count"] or 0),
    )


def assert_truth_source_write_safe(
    snapshot: TruthSourceHealthSnapshot,
    *,
    context: str,
) -> None:
    # 旧投影层还有 active 社区，但 truth-source 已经归零时，任何破坏性脚本都必须停住。
    if (
        snapshot.enabled_registry_count == 0
        and (snapshot.active_pool_count > 0 or snapshot.active_cache_count > 0)
    ):
        raise RuntimeError(
            f"{context}: truth-source is unhealthy; active legacy projection exists "
            "while enabled truth rows are zero. Restore truth-source before destructive writes."
        )


def assert_restore_truth_health(
    snapshot: TruthSourceHealthSnapshot,
    *,
    expected_enabled_min: int,
    context: str,
) -> None:
    if expected_enabled_min <= 0:
        return
    if snapshot.enabled_registry_count < expected_enabled_min:
        raise RuntimeError(
            f"{context}: expected at least {expected_enabled_min} enabled truth rows, "
            f"got {snapshot.enabled_registry_count}"
        )
    if snapshot.active_runtime_count == 0:
        raise RuntimeError(
            f"{context}: restore finished with zero active runtime rows; truth-source is not usable"
        )
