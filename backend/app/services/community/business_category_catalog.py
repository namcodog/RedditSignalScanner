from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_category import BusinessCategory
from app.services.community.business_category_config import (
    BusinessCategoryDefinition,
    load_business_category_config,
)


def canonical_business_categories() -> tuple[BusinessCategoryDefinition, ...]:
    return load_business_category_config().categories


def canonical_business_category_keys() -> list[str]:
    return [item.key for item in canonical_business_categories()]


async def ensure_business_category_catalog(
    session: AsyncSession,
    *,
    keys: Sequence[str] | None = None,
) -> list[str]:
    requested = set(keys or canonical_business_category_keys())
    catalog = {item.key: item for item in canonical_business_categories() if item.key in requested}
    if not catalog:
        return []

    rows = await session.execute(
        select(BusinessCategory).where(BusinessCategory.key.in_(catalog.keys()))
    )
    existing = {row.key: row for row in rows.scalars()}
    written: list[str] = []

    for key, item in catalog.items():
        row = existing.get(key)
        if row is None:
            session.add(
                BusinessCategory(
                    key=key,
                    display_name=item.display_name,
                    description=item.description,
                    is_active=True,
                )
            )
            written.append(key)
            continue
        changed = False
        if row.display_name != item.display_name:
            row.display_name = item.display_name
            changed = True
        if row.description != item.description:
            row.description = item.description
            changed = True
        if not row.is_active:
            row.is_active = True
            changed = True
        if changed:
            written.append(key)

    await session.flush()
    return written


__all__ = [
    "canonical_business_categories",
    "canonical_business_category_keys",
    "ensure_business_category_catalog",
]
