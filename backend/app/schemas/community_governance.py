from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.base import ORMModel


class GovernanceDataSourceContract(ORMModel):
    category_source: str
    category_source_notes: str


class GovernanceSummary(ORMModel):
    effective_pool_count: int = Field(ge=0)
    effective_unclassified_count: int = Field(ge=0)
    category_breakdown: dict[str, int] = Field(default_factory=dict)
    candidate_count: int = Field(ge=0)
    pool_garbage_count: int = Field(ge=0)
    historical_shell_count: int = Field(ge=0)
    discovered_garbage_count: int = Field(ge=0)
    anomaly_count: int = Field(ge=0)


class GovernancePoolCommunityItem(ORMModel):
    id: int | None = None
    name: str
    tier: str | None = None
    priority: str | None = None
    categories: Any = None
    normalized_categories: list[str] = Field(default_factory=list)
    category_source: str
    health_status: str | None = None
    discovered_count: int | None = Field(default=None, ge=0)
    quality_score: float | None = None
    is_active: bool
    is_blacklisted: bool
    config_blacklisted: bool
    deleted_at: str | None = None


class GovernanceHistoricalShellItem(GovernancePoolCommunityItem):
    has_posts_raw: bool
    has_community_audit: bool
    has_category_map: bool
    blocked_reason: str
    touch_policy: str


class GovernanceDiscoveredCommunityItem(ORMModel):
    id: int | None = None
    name: str
    status: str | None = None
    normalized_categories: list[str] = Field(default_factory=list)
    category_source: str | None = None
    discovered_count: int | None = Field(default=None, ge=0)
    cooldown_until: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    deleted_at: str | None = None
    reason: str | None = None


class GovernanceGarbageCommunities(ORMModel):
    pool: list[GovernancePoolCommunityItem] = Field(default_factory=list)
    discovered: list[GovernanceDiscoveredCommunityItem] = Field(default_factory=list)


class GovernanceSnapshot(ORMModel):
    data_source_contract: GovernanceDataSourceContract
    summary: GovernanceSummary
    effective_communities: list[GovernancePoolCommunityItem] = Field(default_factory=list)
    candidate_communities: list[GovernanceDiscoveredCommunityItem] = Field(default_factory=list)
    garbage_communities: GovernanceGarbageCommunities
    historical_shells: list[GovernanceHistoricalShellItem] = Field(default_factory=list)
    anomalies: list[GovernanceDiscoveredCommunityItem] = Field(default_factory=list)


class GovernanceCleanupDeletedCounts(ORMModel):
    pool: int = Field(ge=0)
    cache: int = Field(ge=0)
    discovered: int = Field(ge=0)


class GovernanceCleanupBlockedCounts(ORMModel):
    pool: int = Field(ge=0)


class GovernanceCleanupTargets(ORMModel):
    pool_names: list[str] = Field(default_factory=list)
    cache_names: list[str] = Field(default_factory=list)
    historical_shell_names: list[str] = Field(default_factory=list)
    discovered_ids: list[int] = Field(default_factory=list)


class GovernanceCleanupBlockedItems(ORMModel):
    pool: list[GovernanceHistoricalShellItem] = Field(default_factory=list)


class GovernanceCleanupResult(ORMModel):
    database: str
    dry_run: bool
    deleted: GovernanceCleanupDeletedCounts
    blocked: GovernanceCleanupBlockedCounts
    summary_before: GovernanceSummary
    summary_after: GovernanceSummary | None = None
    targets: GovernanceCleanupTargets
    blocked_items: GovernanceCleanupBlockedItems
    anomalies: list[GovernanceDiscoveredCommunityItem] = Field(default_factory=list)


__all__ = [
    "GovernanceCleanupBlockedCounts",
    "GovernanceCleanupBlockedItems",
    "GovernanceCleanupDeletedCounts",
    "GovernanceCleanupResult",
    "GovernanceCleanupTargets",
    "GovernanceDataSourceContract",
    "GovernanceDiscoveredCommunityItem",
    "GovernanceGarbageCommunities",
    "GovernanceHistoricalShellItem",
    "GovernancePoolCommunityItem",
    "GovernanceSnapshot",
    "GovernanceSummary",
]
