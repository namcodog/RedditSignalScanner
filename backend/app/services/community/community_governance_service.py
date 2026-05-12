from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database_guard import _extract_database_name
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.models.discovered_community import DiscoveredCommunity
from app.schemas.community_governance import (
    GovernanceCleanupBlockedCounts,
    GovernanceCleanupBlockedItems,
    GovernanceCleanupDeletedCounts,
    GovernanceCleanupResult,
    GovernanceCleanupTargets,
    GovernanceDataSourceContract,
    GovernanceDiscoveredCommunityItem,
    GovernanceGarbageCommunities,
    GovernanceHistoricalShellItem,
    GovernancePoolCommunityItem,
    GovernanceSnapshot,
    GovernanceSummary,
)
from app.services.community.blacklist_loader import get_blacklist_config


COMMUNITY_CLEANUP_ALLOWED_DATABASES = {
    "reddit_signal_scanner_dev",
    "reddit_signal_scanner_test",
    "reddit_scanner_test",
}


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_categories(value: Any) -> list[str]:
    items: list[str] = []

    def _add(candidate: Any) -> None:
        normalized = str(candidate or "").strip()
        if normalized:
            items.append(normalized)

    if isinstance(value, dict):
        for nested in value.values():
            if isinstance(nested, (list, tuple, set)):
                for item in nested:
                    _add(item)
            else:
                _add(nested)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            _add(item)
    else:
        _add(value)

    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _build_category_breakdown(items: list[GovernancePoolCommunityItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        normalized_categories = item.normalized_categories or []
        if not normalized_categories:
            counts["unclassified"] = counts.get("unclassified", 0) + 1
            continue
        for category in normalized_categories:
            counts[category] = counts.get(category, 0) + 1
    return {key: counts[key] for key in sorted(counts)}


class CommunityGovernanceService:
    """统一输出社区治理快照，并提供 Dev/Test 清理入口。"""

    def __init__(self, session: AsyncSession, *, database_url: str) -> None:
        self._session = session
        self._database_url = database_url

    async def build_snapshot(self) -> GovernanceSnapshot:
        pool_rows = (
            await self._session.execute(select(CommunityPool).order_by(CommunityPool.name))
        ).scalars().all()
        discovered_rows = (
            await self._session.execute(
                select(DiscoveredCommunity).order_by(DiscoveredCommunity.name, DiscoveredCommunity.id)
            )
        ).scalars().all()

        blacklist = get_blacklist_config()
        effective_communities: list[GovernancePoolCommunityItem] = []
        garbage_pool: list[GovernancePoolCommunityItem] = []
        historical_shells: list[GovernanceHistoricalShellItem] = []
        candidate_communities: list[GovernanceDiscoveredCommunityItem] = []
        garbage_discovered: list[GovernanceDiscoveredCommunityItem] = []
        anomalies: list[GovernanceDiscoveredCommunityItem] = []
        reference_statuses = await self._load_pool_reference_statuses(
            [int(row.id) for row in pool_rows if row.id is not None]
        )

        effective_names: set[str] = set()

        for row in pool_rows:
            row_name = str(row.name or "").strip()
            config_blacklisted = blacklist.is_community_blacklisted(row_name)
            serialized = self._serialize_pool_row(
                row,
                config_blacklisted=config_blacklisted,
            )
            if (
                row.is_active
                and row.deleted_at is None
                and not row.is_blacklisted
                and not config_blacklisted
            ):
                effective_communities.append(serialized)
                effective_names.add(row_name.lower())
            else:
                refs = reference_statuses.get(
                    int(row.id),
                    {
                        "has_posts_raw": False,
                        "has_community_audit": False,
                        "has_category_map": False,
                    },
                )
                if refs["has_posts_raw"] or refs["has_community_audit"] or refs["has_category_map"]:
                    historical_shells.append(
                        GovernanceHistoricalShellItem(
                            **serialized.model_dump(),
                            **refs,
                            # B2 隔离合同: shell 不是有效社区也不是候选，因历史引用异常不删。
                            # 陪同 historical 引用内容一起死，经运营层人工确认查表前禁止任何恢复和激活操作。
                            blocked_reason="has_historical_references",
                            touch_policy="do_not_restore_or_activate",
                        )
                    )
                else:
                    garbage_pool.append(serialized)

        for row in discovered_rows:
            serialized = self._serialize_discovered_row(row)
            row_name = str(row.name or "").strip().lower()
            status = str(row.status or "").strip().lower()

            if row.deleted_at is not None:
                garbage_discovered.append(serialized.model_copy(update={"reason": "soft_deleted"}))
                continue

            if status == "pending":
                if row_name in effective_names:
                    garbage_discovered.append(
                        serialized.model_copy(update={"reason": "pending_duplicate_in_effective_pool"})
                    )
                else:
                    candidate_communities.append(serialized)
                continue

            if status in {"rejected", "blacklisted"}:
                garbage_discovered.append(
                    serialized.model_copy(update={"reason": f"status_{status}"})
                )
                continue

            if status == "approved":
                if row_name in effective_names:
                    garbage_discovered.append(
                        serialized.model_copy(update={"reason": "approved_duplicate_in_effective_pool"})
                    )
                else:
                    anomalies.append(
                        serialized.model_copy(update={"reason": "approved_without_effective_pool"})
                    )
                continue

            anomalies.append(
                serialized.model_copy(update={"reason": f"unexpected_status_{status or 'unknown'}"})
            )

        category_breakdown = _build_category_breakdown(effective_communities)
        effective_unclassified_count = category_breakdown.get("unclassified", 0)

        return GovernanceSnapshot(
            # B1 分类真相源合同: 当前活跃社区的分类真相源是 community_pool.categories。
            # community_category_map / vertical_map 是历史配套表，不作为当前快照的主源。
            # 禁止在其他文件或代码中另建领域列表。
            data_source_contract=GovernanceDataSourceContract(
                category_source="community_pool.categories",
                category_source_notes=(
                    "community_category_map and vertical_map are historical companion tables, "
                    "not the authoritative source for the current governance snapshot."
                ),
            ),
            summary=GovernanceSummary(
                effective_pool_count=len(effective_communities),
                effective_unclassified_count=effective_unclassified_count,
                category_breakdown=category_breakdown,
                candidate_count=len(candidate_communities),
                pool_garbage_count=len(garbage_pool),
                historical_shell_count=len(historical_shells),
                discovered_garbage_count=len(garbage_discovered),
                anomaly_count=len(anomalies),
            ),
            effective_communities=effective_communities,
            candidate_communities=candidate_communities,
            garbage_communities=GovernanceGarbageCommunities(
                pool=garbage_pool,
                discovered=garbage_discovered,
            ),
            historical_shells=historical_shells,
            anomalies=anomalies,
        )

    async def cleanup_dev(self, *, dry_run: bool) -> GovernanceCleanupResult:
        db_name = _extract_database_name(self._database_url)
        if db_name not in COMMUNITY_CLEANUP_ALLOWED_DATABASES:
            raise RuntimeError(
                f"Community cleanup is allowed only on dev/test databases, got: {db_name or 'unknown'}"
            )

        snapshot = await self.build_snapshot()
        pool_delete_names = [
            item.name for item in snapshot.garbage_communities.pool if item.name
        ]
        blocked_pool_items = list(snapshot.historical_shells)
        cache_delete_names = [
            item.name
            for item in [*snapshot.garbage_communities.pool, *snapshot.historical_shells]
            if item.name
        ]
        discovered_delete_ids = [
            int(item.id)
            for item in snapshot.garbage_communities.discovered
            if item.id is not None
        ]

        result = GovernanceCleanupResult(
            database=db_name,
            dry_run=dry_run,
            deleted=GovernanceCleanupDeletedCounts(
                pool=len(pool_delete_names),
                cache=len(cache_delete_names),
                discovered=len(discovered_delete_ids),
            ),
            blocked=GovernanceCleanupBlockedCounts(pool=len(blocked_pool_items)),
            summary_before=snapshot.summary,
            targets=GovernanceCleanupTargets(
                pool_names=pool_delete_names,
                cache_names=cache_delete_names,
                historical_shell_names=[item.name for item in blocked_pool_items if item.name],
                discovered_ids=discovered_delete_ids,
            ),
            blocked_items=GovernanceCleanupBlockedItems(pool=blocked_pool_items),
            anomalies=snapshot.anomalies,
        )

        if dry_run:
            return result

        if cache_delete_names:
            await self._session.execute(
                delete(CommunityCache).where(CommunityCache.community_name.in_(cache_delete_names))
            )

        if pool_delete_names:
            await self._session.execute(
                delete(CommunityPool).where(CommunityPool.name.in_(pool_delete_names))
            )

        if discovered_delete_ids:
            await self._session.execute(
                delete(DiscoveredCommunity).where(DiscoveredCommunity.id.in_(discovered_delete_ids))
            )

        await self._session.commit()
        summary_after = (await self.build_snapshot()).summary
        return result.model_copy(update={"summary_after": summary_after})

    async def _load_pool_reference_statuses(
        self,
        community_ids: list[int],
    ) -> dict[int, dict[str, bool]]:
        if not community_ids:
            return {}

        table_presence = (
            await self._session.execute(
                text(
                    """
                    SELECT
                        to_regclass('public.posts_raw') IS NOT NULL AS has_posts_raw_table,
                        to_regclass('public.community_audit') IS NOT NULL AS has_community_audit_table,
                        to_regclass('public.community_category_map') IS NOT NULL AS has_category_map_table
                    """
                )
            )
        ).one()
        posts_raw_expr = (
            "EXISTS(SELECT 1 FROM posts_raw WHERE community_id = p.id)"
            if table_presence.has_posts_raw_table
            else "FALSE"
        )
        community_audit_expr = (
            "EXISTS(SELECT 1 FROM community_audit WHERE community_id = p.id)"
            if table_presence.has_community_audit_table
            else "FALSE"
        )
        category_map_expr = (
            "EXISTS(SELECT 1 FROM community_category_map WHERE community_id = p.id)"
            if table_presence.has_category_map_table
            else "FALSE"
        )

        rows = (
            await self._session.execute(
                text(
                    f"""
                    SELECT
                        p.id AS community_id,
                        {posts_raw_expr} AS has_posts_raw,
                        {community_audit_expr} AS has_community_audit,
                        {category_map_expr} AS has_category_map
                    FROM community_pool p
                    WHERE p.id = ANY(:community_ids)
                    """
                ).bindparams(community_ids=community_ids)
            )
        ).all()
        return {
            int(row.community_id): {
                "has_posts_raw": bool(row.has_posts_raw),
                "has_community_audit": bool(row.has_community_audit),
                "has_category_map": bool(row.has_category_map),
            }
            for row in rows
        }

    @staticmethod
    def _serialize_pool_row(
        row: CommunityPool,
        *,
        config_blacklisted: bool,
    ) -> GovernancePoolCommunityItem:
        normalized_categories = _normalize_categories(row.categories)
        return GovernancePoolCommunityItem(
            id=row.id,
            name=str(row.name or ""),
            tier=row.tier,
            priority=row.priority,
            categories=row.categories,
            normalized_categories=normalized_categories,
            category_source="community_pool.categories",
            health_status=row.health_status,
            discovered_count=row.discovered_count,
            quality_score=_as_float(row.quality_score),
            is_active=bool(row.is_active),
            is_blacklisted=bool(row.is_blacklisted),
            config_blacklisted=config_blacklisted,
            deleted_at=row.deleted_at.isoformat() if row.deleted_at else None,
        )

    @staticmethod
    def _serialize_discovered_row(row: DiscoveredCommunity) -> GovernanceDiscoveredCommunityItem:
        return GovernanceDiscoveredCommunityItem(
            id=row.id,
            name=str(row.name or ""),
            status=row.status,
            normalized_categories=[],
            category_source=None,
            discovered_count=row.discovered_count,
            cooldown_until=row.cooldown_until.isoformat() if row.cooldown_until else None,
            metrics=row.metrics or {},
            deleted_at=row.deleted_at.isoformat() if row.deleted_at else None,
        )


__all__ = ["CommunityGovernanceService"]
