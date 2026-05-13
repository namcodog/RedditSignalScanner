from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand_registry import BrandMention, BrandRegistry
from app.services.brand_intelligence.brand_consumer_profile import (
    load_brand_consumer_profile,
)


@dataclass(frozen=True)
class BrandEvidenceRow:
    brand_key: str
    display_name: str
    evidence_status: str
    business_domains: tuple[str, ...]
    interest_tags: tuple[str, ...]
    mention_count: int
    communities: tuple[str, ...]
    latest_observed_at: str | None = None


async def load_brand_system_evidence(
    session: AsyncSession,
    *,
    profile_id: str = "system_evidence",
    min_mentions: int = 1,
    limit: int = 100,
) -> dict[str, object]:
    profile = load_brand_consumer_profile(profile_id)
    if profile.review_statuses:
        statuses = profile.review_statuses
    else:
        statuses = ()
    rows = await _load_rows(
        session,
        statuses=statuses,
        exclude_risk_flags=profile.exclude_risk_flags,
        min_mentions=max(1, min_mentions),
        limit=max(1, limit),
    )
    return build_brand_system_evidence_payload(rows, profile_id=profile.profile_id)


def build_brand_system_evidence_payload(
    rows: Sequence[BrandEvidenceRow],
    *,
    profile_id: str,
) -> dict[str, object]:
    ordered = sorted(
        rows, key=lambda row: (-row.mention_count, row.display_name.lower())
    )
    return {
        "phase": "brand-intelligence-r16-system-evidence",
        "source": "brand_registry + brand_mentions",
        "db_writes": False,
        "frontend_display": False,
        "miniapp_snapshot_fields": False,
        "profile": profile_id,
        "summary": _summary(ordered),
        "system_contract": {
            "not_frontend_surface": True,
            "main_system_uses": [
                "community_recommendation_explanations",
                "hotpost_card_context",
                "semantic_review_queue",
            ],
            "miniapp_benefit": "indirect_card_quality_and_reasoning",
        },
        "interest_tag_evidence": _tag_evidence(ordered),
        "community_brand_evidence": _community_evidence(ordered),
    }


async def _load_rows(
    session: AsyncSession,
    *,
    statuses: tuple[str, ...],
    exclude_risk_flags: bool,
    min_mentions: int,
    limit: int,
) -> tuple[BrandEvidenceRow, ...]:
    mention_count = func.count(BrandMention.id)
    communities = func.array_agg(func.distinct(BrandMention.community)).filter(
        BrandMention.community.is_not(None)
    )
    stmt = (
        select(
            BrandRegistry,
            mention_count,
            communities,
            func.max(BrandMention.observed_at),
        )
        .join(BrandMention, BrandMention.brand_id == BrandRegistry.id)
        .where(BrandRegistry.is_active.is_(True))
        .group_by(BrandRegistry.id)
        .having(mention_count >= min_mentions)
        .order_by(mention_count.desc(), BrandRegistry.canonical_name)
        .limit(limit)
    )
    if statuses:
        stmt = stmt.where(BrandRegistry.review_status.in_(statuses))
    if exclude_risk_flags:
        stmt = stmt.where(func.cardinality(BrandRegistry.risk_flags) == 0)
    result = await session.execute(stmt)
    return tuple(_row_from_result(*item) for item in result.all())


def _row_from_result(
    brand: BrandRegistry,
    mention_count: int,
    communities: Sequence[str] | None,
    latest: datetime | None,
) -> BrandEvidenceRow:
    return BrandEvidenceRow(
        brand_key=brand.brand_key,
        display_name=brand.canonical_name,
        evidence_status=brand.review_status,
        business_domains=tuple(brand.domains),
        interest_tags=tuple(brand.interest_tags),
        mention_count=int(mention_count),
        communities=tuple(sorted(item for item in (communities or ()) if item)),
        latest_observed_at=latest.isoformat() if latest else None,
    )


def _summary(rows: Sequence[BrandEvidenceRow]) -> dict[str, object]:
    return {
        "brand_count": len(rows),
        "mention_count": sum(row.mention_count for row in rows),
        "interest_tag_count": len({tag for row in rows for tag in row.interest_tags}),
        "community_count": len(
            {community for row in rows for community in row.communities}
        ),
    }


def _tag_evidence(rows: Sequence[BrandEvidenceRow]) -> list[dict[str, object]]:
    grouped: dict[str, list[BrandEvidenceRow]] = {}
    for row in rows:
        for tag in row.interest_tags:
            grouped.setdefault(tag, []).append(row)
    return [
        _group_payload(tag, items, "interest_tag")
        for tag, items in _sorted_groups(grouped)
    ]


def _community_evidence(rows: Sequence[BrandEvidenceRow]) -> list[dict[str, object]]:
    grouped: dict[str, list[BrandEvidenceRow]] = {}
    for row in rows:
        for community in row.communities:
            grouped.setdefault(community, []).append(row)
    return [
        _group_payload(community, items, "community")
        for community, items in _sorted_groups(grouped)
    ]


def _group_payload(
    name: str, rows: list[BrandEvidenceRow], key: str
) -> dict[str, object]:
    ordered = sorted(
        rows, key=lambda row: (-row.mention_count, row.display_name.lower())
    )
    return {
        key: name,
        "brand_count": len({row.brand_key for row in rows}),
        "mention_count": sum(row.mention_count for row in rows),
        "top_brands": ", ".join(row.display_name for row in ordered[:5]),
        "brands": [_brand_payload(row) for row in ordered[:8]],
    }


def _brand_payload(row: BrandEvidenceRow) -> dict[str, object]:
    return {
        "brand_key": row.brand_key,
        "display_name": row.display_name,
        "evidence_status": row.evidence_status,
        "business_domains": list(row.business_domains),
        "interest_tags": list(row.interest_tags),
        "mention_count": row.mention_count,
        "communities": list(row.communities),
        "latest_observed_at": row.latest_observed_at,
    }


def _sorted_groups(
    groups: dict[str, list[BrandEvidenceRow]]
) -> list[tuple[str, list[BrandEvidenceRow]]]:
    return sorted(
        groups.items(),
        key=lambda item: (-sum(row.mention_count for row in item[1]), item[0]),
    )
