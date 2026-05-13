from __future__ import annotations

from collections.abc import Mapping, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand_registry import BrandMention, BrandRegistry
from app.services.brand_intelligence.brand_consumer_profile import (
    BrandConsumerProfile,
    load_brand_consumer_profile,
)


async def read_brand_registry_view(
    session: AsyncSession,
    *,
    status_filter: str | None = None,
    interest_tag_filter: str | None = None,
    limit: int = 100,
    consumer_profile_id: str = "consumer_safe",
) -> dict[str, object]:
    consumer_profile = load_brand_consumer_profile(consumer_profile_id)
    rows = await _load_registry_rows(
        session,
        status_filter=status_filter,
        interest_tag_filter=interest_tag_filter,
        limit=limit,
        consumer_profile=consumer_profile,
    )
    counts = await _load_mention_counts(session, [row.brand_key for row in rows])
    return build_brand_registry_view_payload(
        rows,
        mention_counts=counts,
        status_filter=status_filter,
        interest_tag_filter=interest_tag_filter,
        consumer_profile=consumer_profile,
    )


def build_brand_registry_view_payload(
    rows: Sequence[BrandRegistry],
    *,
    mention_counts: Mapping[str, int],
    status_filter: str | None,
    interest_tag_filter: str | None,
    consumer_profile: BrandConsumerProfile,
) -> dict[str, object]:
    brands = [
        _brand_payload(row, mention_counts.get(row.brand_key, 0), consumer_profile)
        for row in rows
    ]
    mention_total = sum(mention_counts.get(row.brand_key, 0) for row in rows)
    return {
        "phase": "brand-intelligence-r15-4-read-only-service",
        "source": "brand_registry",
        "db_writes": False,
        "consumer_profile": consumer_profile.profile_id,
        "field_contract_version": consumer_profile.field_contract_version,
        "summary": {
            "returned_brands": len(brands),
            "status_filter": status_filter or "",
            "interest_tag_filter": interest_tag_filter or "",
            "mention_count": mention_total,
        },
        "consumer_contract": {
            "shared_backend_source": "brand_registry",
            "read_only_service": "brand_registry_reader",
            "main_system": True,
            "api_frontend_miniapp_can_share": True,
            "include_internal_fields": consumer_profile.include_internal_fields,
            "miniapp_snapshot_fields": False,
            "miniapp_product_review_required": True,
        },
        "brands": brands,
    }


def render_brand_registry_view_markdown(payload: Mapping[str, object]) -> str:
    summary = _mapping(payload.get("summary"))
    rows = _list_of_mappings(payload.get("brands"))
    lines = [
        "# Brand Registry Read-only View",
        "",
        f"- source: `{payload.get('source', '')}`",
        f"- db_writes: `{_bool_text(payload.get('db_writes'))}`",
        f"- returned_brands: `{summary.get('returned_brands', 0)}`",
        f"- status_filter: `{summary.get('status_filter', '')}`",
        f"- interest_tag_filter: `{summary.get('interest_tag_filter', '')}`",
        "",
        "| Brand | Key | Status | Mentions | Tags |",
        "|---|---:|---:|---:|---|",
    ]
    lines.extend(
        "| "
        + " | ".join(
            [
                _cell(_text(row.get("display_name") or row.get("canonical_name"))),
                _cell(str(row.get("brand_key", ""))),
                _cell(
                    _text(
                        row.get("display_status")
                        or row.get("review_status")
                        or row.get("evidence_status")
                    )
                ),
                str(row.get("mention_count", 0)),
                _cell(", ".join(_strings(row.get("interest_tags")))),
            ]
        )
        + " |"
        for row in rows
    )
    if not rows:
        lines.append("| none |  |  | 0 |  |")
    return "\n".join(lines) + "\n"


async def _load_registry_rows(
    session: AsyncSession,
    *,
    status_filter: str | None,
    interest_tag_filter: str | None,
    limit: int,
    consumer_profile: BrandConsumerProfile,
) -> Sequence[BrandRegistry]:
    stmt = select(BrandRegistry).where(BrandRegistry.is_active.is_(True))
    statuses = _effective_statuses(status_filter, consumer_profile)
    if consumer_profile.review_statuses and not statuses:
        return ()
    if statuses:
        stmt = stmt.where(BrandRegistry.review_status.in_(statuses))
    if interest_tag_filter:
        stmt = stmt.where(BrandRegistry.interest_tags.contains([interest_tag_filter]))
    result = await session.execute(
        stmt.order_by(BrandRegistry.canonical_name).limit(limit)
    )
    rows: Sequence[BrandRegistry] = result.scalars().all()
    return rows


async def _load_mention_counts(
    session: AsyncSession, keys: Sequence[str]
) -> dict[str, int]:
    if not keys:
        return {}
    stmt = (
        select(BrandMention.brand_key, func.count(BrandMention.id))
        .where(BrandMention.brand_key.in_(keys))
        .group_by(BrandMention.brand_key)
    )
    result = await session.execute(stmt)
    return {str(key): int(count) for key, count in result.all()}


def _brand_payload(
    row: BrandRegistry, mention_count: int, profile: BrandConsumerProfile
) -> dict[str, object]:
    if profile.include_internal_fields:
        return {
            "brand_key": row.brand_key,
            "canonical_name": row.canonical_name,
            "review_status": row.review_status,
            "source_lifecycle": row.source_lifecycle,
            "domains": list(row.domains),
            "interest_tags": list(row.interest_tags),
            "risk_flags": list(row.risk_flags),
            "mention_count": mention_count,
        }
    return {
        "brand_key": row.brand_key,
        "display_name": row.canonical_name,
        "business_domains": list(row.domains),
        "interest_tags": list(row.interest_tags),
        "evidence_status": row.review_status,
        "display_status": profile.display_statuses.get(
            row.review_status, row.review_status
        ),
        "mention_count": mention_count,
    }


def _effective_statuses(
    status_filter: str | None, profile: BrandConsumerProfile
) -> tuple[str, ...]:
    if not profile.review_statuses:
        return (status_filter,) if status_filter else ()
    if status_filter:
        return (status_filter,) if status_filter in profile.review_statuses else ()
    return profile.review_statuses


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _list_of_mappings(value: object) -> list[Mapping[str, object]]:
    return (
        [item for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def _strings(value: object) -> list[str]:
    return (
        [item for item in value if isinstance(item, str)]
        if isinstance(value, list)
        else []
    )


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _cell(value: str) -> str:
    return value.replace("|", "\\|")
