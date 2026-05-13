from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


@dataclass(slots=True)
class TruthSourceReadinessSnapshot:
    truth_tables_ready: bool
    missing_truth_tables: list[str]
    enabled_registry_count: int
    registry_with_current_membership_count: int
    approved_registry_count: int
    active_runtime_count: int
    enabled_registry_missing_membership_count: int
    membership_coverage_ratio: float
    approval_coverage_ratio: float
    approved_registry_runtime_gap_count: int
    approved_registry_runtime_gap_ratio: float
    recent_posts_count: int
    recent_posts_with_semantic_count: int
    recent_posts_semantic_coverage_ratio: float

    def as_dict(self) -> dict[str, int | float | bool | list[str]]:
        return asdict(self)


async def _load_truth_table_status(session: AsyncSession) -> list[str]:
    row = (
        await session.execute(
            text(
                """
                SELECT
                  to_regclass('public.community_registry') IS NOT NULL AS community_registry,
                  to_regclass('public.community_domain_membership') IS NOT NULL AS community_domain_membership,
                  to_regclass('public.community_governance_decision') IS NOT NULL AS community_governance_decision,
                  to_regclass('public.community_runtime_state') IS NOT NULL AS community_runtime_state,
                  to_regclass('public.semantic_observation') IS NOT NULL AS semantic_observation
                """
            )
        )
    ).mappings().one()
    return [name for name, ready in row.items() if not bool(ready)]


async def read_truth_source_readiness_snapshot(
    session: AsyncSession,
    *,
    lookback_days: int,
) -> TruthSourceReadinessSnapshot:
    missing_tables = await _load_truth_table_status(session)
    if missing_tables:
        return TruthSourceReadinessSnapshot(
            truth_tables_ready=False,
            missing_truth_tables=missing_tables,
            enabled_registry_count=0,
            registry_with_current_membership_count=0,
            approved_registry_count=0,
            active_runtime_count=0,
            enabled_registry_missing_membership_count=0,
            membership_coverage_ratio=0.0,
            approval_coverage_ratio=0.0,
            approved_registry_runtime_gap_count=0,
            approved_registry_runtime_gap_ratio=0.0,
            recent_posts_count=0,
            recent_posts_with_semantic_count=0,
            recent_posts_semantic_coverage_ratio=0.0,
        )

    row = (
        await session.execute(
            text(
                """
                WITH enabled_registry AS (
                  SELECT id
                  FROM community_registry
                  WHERE platform = 'reddit'
                    AND is_enabled = TRUE
                ),
                current_membership AS (
                  SELECT DISTINCT community_id
                  FROM community_domain_membership
                  WHERE is_current = TRUE
                ),
                approved_registry AS (
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
                ),
                recent_posts AS (
                  SELECT id
                  FROM posts_raw
                  WHERE created_at >= now() - make_interval(days => :lookback_days)
                ),
                recent_semantic_posts AS (
                  SELECT COUNT(DISTINCT so.content_id) AS total
                  FROM semantic_observation so
                  JOIN recent_posts p ON p.id = so.content_id
                  WHERE so.content_type = 'post'
                )
                SELECT
                  (SELECT COUNT(*) FROM enabled_registry) AS enabled_registry_count,
                  (
                    SELECT COUNT(*)
                    FROM current_membership
                    WHERE community_id IN (SELECT id FROM enabled_registry)
                  ) AS registry_with_current_membership_count,
                  (
                    SELECT COUNT(*)
                    FROM approved_registry
                    WHERE community_id IN (SELECT id FROM enabled_registry)
                  ) AS approved_registry_count,
                  (
                    SELECT COUNT(*)
                    FROM active_runtime
                    WHERE community_id IN (SELECT community_id FROM approved_registry)
                  ) AS active_runtime_count,
                  (SELECT COUNT(*) FROM recent_posts) AS recent_posts_count,
                  (SELECT total FROM recent_semantic_posts) AS recent_posts_with_semantic_count
                """
            ),
            {"lookback_days": lookback_days},
        )
    ).mappings().one()

    enabled_registry_count = int(row["enabled_registry_count"] or 0)
    registry_with_current_membership_count = int(
        row["registry_with_current_membership_count"] or 0
    )
    approved_registry_count = int(row["approved_registry_count"] or 0)
    active_runtime_count = int(row["active_runtime_count"] or 0)
    recent_posts_count = int(row["recent_posts_count"] or 0)
    recent_posts_with_semantic_count = int(
        row["recent_posts_with_semantic_count"] or 0
    )
    enabled_registry_missing_membership_count = max(
        enabled_registry_count - registry_with_current_membership_count,
        0,
    )
    approved_registry_runtime_gap_count = max(
        approved_registry_count - active_runtime_count,
        0,
    )

    return TruthSourceReadinessSnapshot(
        truth_tables_ready=True,
        missing_truth_tables=[],
        enabled_registry_count=enabled_registry_count,
        registry_with_current_membership_count=registry_with_current_membership_count,
        approved_registry_count=approved_registry_count,
        active_runtime_count=active_runtime_count,
        enabled_registry_missing_membership_count=enabled_registry_missing_membership_count,
        membership_coverage_ratio=_safe_ratio(
            registry_with_current_membership_count,
            enabled_registry_count,
        ),
        approval_coverage_ratio=_safe_ratio(
            approved_registry_count,
            enabled_registry_count,
        ),
        approved_registry_runtime_gap_count=approved_registry_runtime_gap_count,
        approved_registry_runtime_gap_ratio=_safe_ratio(
            approved_registry_runtime_gap_count,
            approved_registry_count,
        ),
        recent_posts_count=recent_posts_count,
        recent_posts_with_semantic_count=recent_posts_with_semantic_count,
        recent_posts_semantic_coverage_ratio=_safe_ratio(
            recent_posts_with_semantic_count,
            recent_posts_count,
        ),
    )


__all__ = [
    "TruthSourceReadinessSnapshot",
    "read_truth_source_readiness_snapshot",
]
