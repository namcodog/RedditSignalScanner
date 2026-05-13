from __future__ import annotations

from datetime import datetime
from typing import Iterable, Mapping, cast

from sqlalchemy import Table, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand_registry import BrandMention, BrandRegistry
from app.services.brand_intelligence.brand_registry_plan import (
    BrandMentionRow,
    BrandRegistryPlan,
    BrandRegistryRow,
)


async def existing_brand_keys(
    session: AsyncSession,
    rows: Iterable[BrandRegistryRow],
) -> set[str]:
    keys = [row.brand_key for row in rows]
    if not keys:
        return set()
    result = await session.execute(
        select(BrandRegistry.brand_key).where(BrandRegistry.brand_key.in_(keys))
    )
    return {str(value) for value in result.scalars().all()}


async def existing_mention_keys(
    session: AsyncSession,
    rows: Iterable[BrandMentionRow],
) -> set[str]:
    keys = [row.mention_key for row in rows]
    if not keys:
        return set()
    result = await session.execute(
        select(BrandMention.mention_key).where(BrandMention.mention_key.in_(keys))
    )
    return {str(value) for value in result.scalars().all()}


async def apply_brand_registry_plan(
    session: AsyncSession,
    plan: BrandRegistryPlan,
    *,
    database: str,
    dry_run: bool,
) -> dict[str, object]:
    brand_existing = await existing_brand_keys(session, plan.registry_rows)
    mention_existing = await existing_mention_keys(session, plan.mention_rows)
    if dry_run:
        return build_registry_write_result(
            plan,
            database=database,
            dry_run=True,
            existing_brand_keys=brand_existing,
            existing_mention_keys=mention_existing,
            inserted_brand_keys=(),
            inserted_mention_keys=(),
        )

    inserted_brand_keys = [
        row.brand_key
        for row in plan.registry_rows
        if row.brand_key not in brand_existing
    ]
    await _upsert_registry_rows(session, plan.registry_rows)
    brand_ids = await _brand_ids_by_key(
        session, [row.brand_key for row in plan.registry_rows]
    )
    inserted_mention_keys = await _insert_mention_rows(
        session,
        plan.mention_rows,
        brand_ids=brand_ids,
        existing_keys=mention_existing,
    )
    await session.commit()
    return build_registry_write_result(
        plan,
        database=database,
        dry_run=False,
        existing_brand_keys=brand_existing,
        existing_mention_keys=mention_existing,
        inserted_brand_keys=inserted_brand_keys,
        inserted_mention_keys=inserted_mention_keys,
    )


def build_registry_write_result(
    plan: BrandRegistryPlan,
    *,
    database: str,
    dry_run: bool,
    existing_brand_keys: set[str],
    existing_mention_keys: set[str],
    inserted_brand_keys: Iterable[str],
    inserted_mention_keys: Iterable[str],
) -> dict[str, object]:
    brand_keys = [row.brand_key for row in plan.registry_rows]
    mention_keys = [row.mention_key for row in plan.mention_rows]
    new_brand_keys = [key for key in brand_keys if key not in existing_brand_keys]
    new_mention_keys = [key for key in mention_keys if key not in existing_mention_keys]
    inserted_brands = list(inserted_brand_keys)
    inserted_mentions = list(inserted_mention_keys)
    return {
        "phase": "brand-intelligence-r15-2-dev-registry",
        "db_writes": not dry_run,
        "database": database,
        "summary": {
            "input_registry_rows": len(brand_keys),
            "input_mentions": len(mention_keys),
            "would_insert_registry_rows": len(new_brand_keys),
            "would_insert_mentions": len(new_mention_keys),
            "inserted_registry_rows": len(inserted_brands),
            "inserted_mentions": len(inserted_mentions),
        },
        "planned_insert_brand_keys": new_brand_keys,
        "planned_insert_mention_keys": new_mention_keys,
        "inserted_brand_keys": inserted_brands,
        "inserted_mention_keys": inserted_mentions,
        "skipped_existing_brand_keys": sorted(existing_brand_keys),
        "skipped_existing_mention_keys": sorted(existing_mention_keys),
    }


async def _upsert_registry_rows(
    session: AsyncSession, rows: tuple[BrandRegistryRow, ...]
) -> None:
    if not rows:
        return
    values = [_registry_values(row) for row in rows]
    stmt = insert(cast(Table, BrandRegistry.__table__)).values(values)
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=["brand_key"],
            set_={
                "canonical_name": stmt.excluded.canonical_name,
                "review_status": stmt.excluded.review_status,
                "source_lifecycle": stmt.excluded.source_lifecycle,
                "domains": stmt.excluded.domains,
                "interest_tags": stmt.excluded.interest_tags,
                "aliases": stmt.excluded.aliases,
                "risk_flags": stmt.excluded.risk_flags,
                "source_payload": stmt.excluded.source_payload,
                "is_active": True,
                "last_seen_at": stmt.excluded.last_seen_at,
            },
        )
    )


async def _brand_ids_by_key(session: AsyncSession, keys: list[str]) -> dict[str, int]:
    if not keys:
        return {}
    result = await session.execute(
        select(BrandRegistry.brand_key, BrandRegistry.id).where(
            BrandRegistry.brand_key.in_(keys)
        )
    )
    return {str(key): int(brand_id) for key, brand_id in result.all()}


async def _insert_mention_rows(
    session: AsyncSession,
    rows: tuple[BrandMentionRow, ...],
    *,
    brand_ids: Mapping[str, int],
    existing_keys: set[str],
) -> list[str]:
    values = [
        _mention_values(row, brand_ids[row.brand_key])
        for row in rows
        if row.mention_key not in existing_keys
    ]
    if not values:
        return []
    stmt = (
        insert(cast(Table, BrandMention.__table__))
        .values(values)
        .on_conflict_do_nothing(index_elements=["mention_key"])
    )
    await session.execute(stmt)
    return [str(value["mention_key"]) for value in values]


def _registry_values(row: BrandRegistryRow) -> dict[str, object]:
    return {
        "brand_key": row.brand_key,
        "canonical_name": row.canonical_name,
        "review_status": row.review_status,
        "source_lifecycle": row.source_lifecycle,
        "domains": list(row.domains),
        "interest_tags": list(row.interest_tags),
        "aliases": list(row.aliases),
        "risk_flags": list(row.risk_flags),
        "source_payload": dict(row.source_payload),
        "is_active": True,
        "first_seen_at": None,
        "last_seen_at": None,
    }


def _mention_values(row: BrandMentionRow, brand_id: int) -> dict[str, object]:
    return {
        "brand_id": brand_id,
        "mention_key": row.mention_key,
        "brand_key": row.brand_key,
        "source": row.source,
        "source_ref": row.source_ref,
        "community": row.community,
        "source_field": row.source_field,
        "source_text": row.source_text,
        "observed_at": _parse_datetime(row.observed_at),
        "permalink": row.permalink,
        "evidence_payload": dict(row.evidence_payload),
    }


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
