from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.community.truth_source_health_guard import (
    assert_truth_source_write_safe,
    read_truth_source_health_snapshot,
)

__all__ = ["DevTruthSourceCompactionResult", "compact_dev_truth_source"]


@dataclass(slots=True)
class DevTruthSourceCompactionResult:
    database: str
    dry_run: bool
    deleted_disabled_registry: int
    deleted_inactive_runtime: int
    deleted_inactive_category_map: int
    deleted_inactive_cache: int
    deleted_inactive_pool: int
    remaining_archived_pool: int
    archived_pool_with_posts: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _assert_dev_database(database_url: str) -> str:
    database = database_url.rsplit("/", 1)[-1].split("?", 1)[0]
    if database not in {"reddit_signal_scanner_dev", "reddit_signal_scanner_test"}:
        raise RuntimeError(f"compaction only allowed on dev/test, got: {database}")
    return database


async def _count_scalar(session: AsyncSession, sql: str) -> int:
    return int((await session.execute(text(sql))).scalar_one() or 0)


async def _table_exists(session: AsyncSession, table_name: str) -> bool:
    return (
        await session.execute(
            text("SELECT to_regclass(:table_name)"),
            {"table_name": f"public.{table_name}"},
        )
    ).scalar_one() is not None


INACTIVE_POOL_SQL = """
SELECT id
FROM community_pool
WHERE NOT is_active
   OR deleted_at IS NOT NULL
   OR COALESCE(is_blacklisted, FALSE)
"""

FINAL_DELETABLE_CACHE_SQL = """
WITH inactive_cache AS (
    SELECT community_name
    FROM community_cache
    WHERE NOT is_active
),
referenced_cache AS (
    SELECT DISTINCT legacy_cache_name AS community_name
    FROM community_runtime_state
    WHERE legacy_cache_name IS NOT NULL
      AND is_enabled
)
SELECT count(*)
FROM inactive_cache c
LEFT JOIN referenced_cache r USING (community_name)
WHERE r.community_name IS NULL
"""


def _final_deletable_pool_ids_sql(*, include_community_audit: bool) -> str:
    community_audit_ref = (
        """
    UNION
    SELECT DISTINCT community_id AS pool_id
    FROM community_audit
    WHERE community_id IS NOT NULL
"""
        if include_community_audit
        else ""
    )
    return f"""
WITH inactive_pool AS (
    {INACTIVE_POOL_SQL}
),
referenced_pool AS (
    SELECT DISTINCT community_id AS pool_id
    FROM posts_raw
    WHERE community_id IS NOT NULL
    {community_audit_ref}
    UNION
    SELECT DISTINCT legacy_pool_id AS pool_id
    FROM community_registry
    WHERE legacy_pool_id IS NOT NULL
      AND is_enabled
)
SELECT p.id
FROM inactive_pool p
LEFT JOIN referenced_pool r ON r.pool_id = p.id
WHERE r.pool_id IS NULL
"""


async def compact_dev_truth_source(
    session: AsyncSession,
    *,
    database_url: str,
    dry_run: bool,
) -> DevTruthSourceCompactionResult:
    database = _assert_dev_database(database_url)
    include_community_audit = await _table_exists(session, "community_audit")
    final_deletable_pool_ids_sql = _final_deletable_pool_ids_sql(
        include_community_audit=include_community_audit
    )
    final_deletable_pool_count_sql = (
        "SELECT count(*) FROM (" + final_deletable_pool_ids_sql + ") AS deletable_pool"
    )
    pre_snapshot = await read_truth_source_health_snapshot(session)
    if not dry_run:
        # 旧投影层还有 active 社区但 truth-source 已归零时，压缩只会把坏状态固化。
        assert_truth_source_write_safe(
            pre_snapshot,
            context="dev truth-source compaction",
        )
    deleted_disabled_registry = await _count_scalar(
        session,
        """
        SELECT count(*)
        FROM community_registry
        WHERE NOT is_enabled
        """,
    )
    deleted_inactive_runtime = await _count_scalar(
        session,
        """
        SELECT count(*)
        FROM community_runtime_state
        WHERE NOT is_enabled
        """,
    )
    deleted_inactive_category_map = await _count_scalar(
        session,
        """
        SELECT count(*)
        FROM community_category_map
        WHERE community_id IN (
            SELECT id
            FROM community_pool
            WHERE NOT is_active
               OR deleted_at IS NOT NULL
               OR COALESCE(is_blacklisted, FALSE)
        )
        """,
    )
    deleted_inactive_cache = await _count_scalar(
        session,
        FINAL_DELETABLE_CACHE_SQL,
    )
    deleted_inactive_pool = await _count_scalar(
        session,
        final_deletable_pool_count_sql,
    )
    archived_pool_with_posts = await _count_scalar(
        session,
        """
        SELECT count(DISTINCT community_id)
        FROM posts_raw
        WHERE community_id IN (
            SELECT id
            FROM community_pool
            WHERE NOT is_active
               OR deleted_at IS NOT NULL
               OR COALESCE(is_blacklisted, FALSE)
        )
        """,
    )

    if not dry_run:
        await session.execute(
            text("DELETE FROM community_registry WHERE NOT is_enabled")
        )
        await session.execute(
            text(
                """
                DELETE FROM community_category_map
                WHERE community_id IN (
                    SELECT id
                    FROM community_pool
                    WHERE NOT is_active
                       OR deleted_at IS NOT NULL
                       OR COALESCE(is_blacklisted, FALSE)
                )
                """
            )
        )
        await session.execute(
            text(
                """
                DELETE FROM community_cache
                WHERE NOT is_active
                  AND community_name NOT IN (
                    SELECT legacy_cache_name
                    FROM community_runtime_state
                    WHERE legacy_cache_name IS NOT NULL
                      AND is_enabled
                  )
                """
            )
        )
        await session.execute(
            text(
                "DELETE FROM community_pool WHERE id IN ("
                + final_deletable_pool_ids_sql
                + ")"
            )
        )
        await session.commit()

    remaining_archived_pool = await _count_scalar(
        session,
        """
        SELECT count(*)
        FROM community_pool
        WHERE NOT is_active
           OR deleted_at IS NOT NULL
           OR COALESCE(is_blacklisted, FALSE)
        """,
    )
    return DevTruthSourceCompactionResult(
        database=database,
        dry_run=dry_run,
        deleted_disabled_registry=deleted_disabled_registry,
        deleted_inactive_runtime=deleted_inactive_runtime,
        deleted_inactive_category_map=deleted_inactive_category_map,
        deleted_inactive_cache=deleted_inactive_cache,
        deleted_inactive_pool=deleted_inactive_pool,
        remaining_archived_pool=remaining_archived_pool,
        archived_pool_with_posts=archived_pool_with_posts,
    )
