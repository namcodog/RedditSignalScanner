from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand_registry import BrandMention, BrandRegistry
from app.services.brand_intelligence.brand_consumer_profile import BrandConsumerProfile
from app.services.brand_intelligence.brand_match_guard import (
    BrandMatchGuard,
    is_brand_text_match_safe,
)
from app.services.brand_intelligence.brand_system_evidence import BrandEvidenceRow


@dataclass(frozen=True)
class BrandMentionRecord:
    brand_key: str
    display_name: str
    evidence_status: str
    business_domains: tuple[str, ...]
    interest_tags: tuple[str, ...]
    source_text: str
    community: str | None
    latest_observed_at: str | None


async def load_brand_evidence_rows(
    session: AsyncSession,
    *,
    profile: BrandConsumerProfile,
    guard: BrandMatchGuard,
    min_mentions: int,
    limit: int,
) -> tuple[BrandEvidenceRow, ...]:
    result = await session.execute(_statement(profile))
    records = tuple(_record_from_result(*item) for item in result.all())
    return build_brand_evidence_rows_from_records(
        records,
        guard=guard,
        min_mentions=min_mentions,
        limit=limit,
    )


def build_brand_evidence_rows_from_records(
    records: Sequence[BrandMentionRecord],
    *,
    guard: BrandMatchGuard,
    min_mentions: int,
    limit: int,
) -> tuple[BrandEvidenceRow, ...]:
    grouped: dict[str, list[BrandMentionRecord]] = {}
    for record in records:
        if is_brand_text_match_safe(
            record.display_name,
            record.evidence_status,
            record.source_text,
            guard,
        ):
            grouped.setdefault(record.brand_key, []).append(record)
    rows = [
        _row_from_records(items)
        for items in grouped.values()
        if len(items) >= max(1, min_mentions)
    ]
    return tuple(
        sorted(rows, key=lambda row: (-row.mention_count, row.display_name.lower()))[
            : max(1, limit)
        ]
    )


def _statement(profile: BrandConsumerProfile) -> object:
    stmt = (
        select(BrandRegistry, BrandMention)
        .join(BrandMention, BrandMention.brand_id == BrandRegistry.id)
        .where(BrandRegistry.is_active.is_(True))
    )
    if profile.review_statuses:
        stmt = stmt.where(BrandRegistry.review_status.in_(profile.review_statuses))
    if profile.exclude_risk_flags:
        stmt = stmt.where(func.cardinality(BrandRegistry.risk_flags) == 0)
    return stmt


def _record_from_result(
    brand: BrandRegistry,
    mention: BrandMention,
) -> BrandMentionRecord:
    return BrandMentionRecord(
        brand_key=brand.brand_key,
        display_name=brand.canonical_name,
        evidence_status=brand.review_status,
        business_domains=tuple(brand.domains),
        interest_tags=tuple(brand.interest_tags),
        source_text=mention.source_text,
        community=mention.community,
        latest_observed_at=_latest(mention.observed_at),
    )


def _row_from_records(records: list[BrandMentionRecord]) -> BrandEvidenceRow:
    first = records[0]
    latest = max((item.latest_observed_at or "" for item in records), default="")
    return BrandEvidenceRow(
        brand_key=first.brand_key,
        display_name=first.display_name,
        evidence_status=first.evidence_status,
        business_domains=first.business_domains,
        interest_tags=first.interest_tags,
        mention_count=len(records),
        communities=tuple(
            sorted({item.community for item in records if item.community})
        ),
        latest_observed_at=latest or None,
    )


def _latest(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
