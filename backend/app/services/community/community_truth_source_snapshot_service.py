from __future__ import annotations

from decimal import Decimal
from typing import Optional, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.community_governance import GovernancePoolCommunityItem


def _as_float(value: object) ->Optional[ float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def load_effective_truth_communities(
    session: AsyncSession,
    *,
    is_config_blacklisted: Callable[[str], bool],
) -> list[GovernancePoolCommunityItem]:
    rows = (
        await session.execute(
            text(
                """
                WITH approved_memberships AS (
                    SELECT DISTINCT membership_id
                    FROM community_governance_decision
                    WHERE is_current = TRUE
                      AND decision = 'approved'
                )
                SELECT
                    r.id AS registry_id,
                    r.community_name,
                    p.id AS pool_id,
                    p.tier,
                    p.priority,
                    p.health_status,
                    p.discovered_count,
                    p.semantic_quality_score AS quality_score,
                    COALESCE(p.is_blacklisted, FALSE) AS pool_blacklisted,
                    p.deleted_at,
                    array_agg(m.domain_key ORDER BY m.is_primary DESC, m.domain_key) AS categories
                FROM community_registry r
                JOIN community_runtime_state s
                  ON s.community_id = r.id
                 AND s.is_enabled = TRUE
                 AND s.crawl_status IN ('active', 'needs_backfill')
                JOIN community_domain_membership m
                  ON m.community_id = r.id
                 AND m.is_current = TRUE
                JOIN approved_memberships a
                  ON a.membership_id = m.id
                LEFT JOIN community_pool p
                  ON p.id = r.legacy_pool_id
                WHERE r.platform = 'reddit'
                  AND r.is_enabled = TRUE
                GROUP BY
                    r.id,
                    r.community_name,
                    p.id,
                    p.tier,
                    p.priority,
                    p.health_status,
                    p.discovered_count,
                    p.semantic_quality_score,
                    p.is_blacklisted,
                    p.deleted_at
                ORDER BY r.community_name
                """
            )
        )
    ).mappings().all()

    items: list[GovernancePoolCommunityItem] = []
    for row in rows:
        name = str(row["community_name"] or "")
        normalized_categories = [str(item) for item in (row["categories"] or []) if item]
        items.append(
            GovernancePoolCommunityItem(
                id=row["pool_id"],
                name=name,
                tier=row["tier"],
                priority=row["priority"],
                categories=normalized_categories,
                normalized_categories=normalized_categories,
                category_source="truth_source.membership",
                health_status=row["health_status"],
                discovered_count=int(row["discovered_count"] or 0),
                quality_score=_as_float(row["quality_score"]),
                is_active=True,
                is_blacklisted=bool(row["pool_blacklisted"]),
                config_blacklisted=is_config_blacklisted(name),
                deleted_at=row["deleted_at"].isoformat() if row["deleted_at"] else None,
            )
        )
    return items


__all__ = ["load_effective_truth_communities"]
