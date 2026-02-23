from __future__ import annotations

from typing import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_CATEGORY_ALIASES = {
    "E-commerce_Ops": "Ecommerce_Business",
}


def _canonical_category_key(key: str) -> str:
    return _CATEGORY_ALIASES.get(key, key)


def _normalize_category_keys(raw: object | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        source: Iterable[object] = raw
    elif isinstance(raw, dict):
        if "categories" in raw and isinstance(raw["categories"], list):
            source = raw["categories"]
        elif "primary" in raw and isinstance(raw["primary"], list):
            source = raw["primary"]
        else:
            source = raw.keys()
    else:
        return []

    seen: set[str] = set()
    keys: list[str] = []
    for item in source:
        if item is None:
            continue
        key = _canonical_category_key(str(item).strip())
        if not key or key in seen:
            continue
        seen.add(key)
        keys.append(key)
    return keys


async def replace_community_category_map(
    db: AsyncSession,
    *,
    community_id: int,
    categories: object | None,
) -> int:
    keys = _normalize_category_keys(categories)

    await db.execute(
        text("DELETE FROM community_category_map WHERE community_id = :community_id"),
        {"community_id": community_id},
    )

    if not keys:
        return 0

    result = await db.execute(
        text(
            """
            WITH incoming AS (
                SELECT key, ord
                FROM unnest(CAST(:keys AS text[])) WITH ORDINALITY AS t(key, ord)
            ),
            filtered AS (
                SELECT DISTINCT ON (incoming.key) incoming.key, incoming.ord
                FROM incoming
                JOIN business_categories bc
                  ON bc.key = incoming.key
                 AND bc.is_active = true
                ORDER BY incoming.key, incoming.ord
            ),
            ordered AS (
                SELECT key, row_number() OVER (ORDER BY ord) AS rn
                FROM filtered
            )
            INSERT INTO community_category_map (community_id, category_key, is_primary)
            SELECT :community_id, key, rn = 1
            FROM ordered
            ORDER BY rn
            RETURNING 1
            """
        ),
        {"community_id": community_id, "keys": keys},
    )
    return int(result.rowcount or 0)
