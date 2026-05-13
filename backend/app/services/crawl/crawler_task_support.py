from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, Callable

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache
from app.services.community.community_pool_loader import CommunityProfile
from app.services.crawl.crawler_config import TierSettings

__all__ = [
    "commit_with_warning",
    "crawler_run_targets_table_exists",
    "env_int",
    "env_truthy",
    "list_stale_caches",
    "load_last_probe_hot_started_at",
    "log_swallowed_exception",
    "mark_empty_hit",
    "mark_failure_hit",
    "maybe_trigger_probe_hot_fallback",
    "planner_lock",
    "rollback_with_warning",
    "tier_settings_for",
]


def log_swallowed_exception(module_logger: Any, context: str, exc: Exception) -> None:
    module_logger.warning("%s: %s", context, exc, exc_info=exc)


async def rollback_with_warning(
    session: AsyncSession,
    *,
    context: str,
    log_swallowed_exception_func: Callable[[str, Exception], None],
) -> None:
    try:
        await session.rollback()
    except Exception as exc:
        log_swallowed_exception_func(f"{context} rollback failed", exc)


async def commit_with_warning(
    session: AsyncSession,
    *,
    context: str,
    rollback_with_warning_func: Callable[[AsyncSession], Any],
    log_swallowed_exception_func: Callable[[str, Exception], None],
) -> bool:
    try:
        await session.commit()
        return True
    except Exception as exc:
        log_swallowed_exception_func(f"{context} commit failed", exc)
        await rollback_with_warning_func(session)
        return False


def tier_settings_for(
    profile: CommunityProfile | None,
    *,
    crawler_config: Any,
) -> TierSettings | None:
    if profile is None:
        return None
    return crawler_config.resolve_tier(profile.tier)


def env_truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y"}


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


async def crawler_run_targets_table_exists(session: AsyncSession) -> bool:
    exists = (
        await session.execute(text("SELECT to_regclass('public.crawler_run_targets')"))
    ).scalar_one_or_none()
    return bool(exists)


@asynccontextmanager
async def planner_lock(
    *,
    session_factory: Callable[[], Any],
    lock_key: str,
    log_swallowed_exception_func: Callable[[str, Exception], None],
) -> AsyncIterator[bool]:
    async with session_factory() as session:
        await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
        acquired = False
        try:
            result = await session.execute(
                text("SELECT pg_try_advisory_lock(hashtext(:key))"),
                {"key": lock_key},
            )
            acquired = bool(result.scalar_one_or_none())
        except Exception as exc:
            log_swallowed_exception_func("planner lock acquire failed", exc)
            acquired = False
        try:
            yield acquired
        finally:
            if acquired:
                try:
                    await session.execute(
                        text("SELECT pg_advisory_unlock(hashtext(:key))"),
                        {"key": lock_key},
                    )
                except Exception as exc:
                    log_swallowed_exception_func("planner lock release failed", exc)


async def load_last_probe_hot_started_at(session: AsyncSession) -> datetime | None:
    result = await session.execute(
        text(
            """
            SELECT MAX(started_at) AS last_started
            FROM crawler_run_targets
            WHERE (config->>'plan_kind') = 'probe'
              AND (config->'meta'->>'source') = 'hot'
            """
        )
    )
    return result.scalar_one_or_none()


async def maybe_trigger_probe_hot_fallback(
    *,
    due_count: int,
    total_pool_count: int,
    session_factory: Callable[[], Any],
    crawler_run_targets_table_exists_func: Callable[[AsyncSession], Any],
    load_last_probe_hot_started_at_func: Callable[[AsyncSession], Any],
    env_truthy_func: Callable[[str, str], bool],
    env_int_func: Callable[[str, int], int],
    send_task: Callable[..., Any],
    module_logger: Any,
) -> bool:
    if not env_truthy_func("PROBE_HOT_FALLBACK_ENABLED", "1"):
        return False

    min_due = max(0, env_int_func("PROBE_HOT_FALLBACK_MIN_DUE", 3))
    if due_count >= min_due:
        return False

    cooldown_minutes = max(
        0, env_int_func("PROBE_HOT_FALLBACK_COOLDOWN_MINUTES", 720)
    )
    posts_per_source = max(
        5, env_int_func("PROBE_HOT_FALLBACK_POSTS_PER_SOURCE", 15)
    )

    async with session_factory() as session:
        if not await crawler_run_targets_table_exists_func(session):
            module_logger.info(
                "probe hot fallback skipped: crawler_run_targets missing"
            )
            return False
        last_started = await load_last_probe_hot_started_at_func(session)

    if last_started is not None:
        if last_started.tzinfo is None:
            last_started = last_started.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - last_started
        if delta < timedelta(minutes=cooldown_minutes):
            module_logger.info(
                "probe hot fallback skipped: cooldown (last=%s, cooldown=%smin)",
                last_started.isoformat(),
                cooldown_minutes,
            )
            return False

    module_logger.info(
        "probe hot fallback triggered: due=%s total_pool=%s",
        due_count,
        total_pool_count,
    )
    try:
        send_task(
            "tasks.probe.run_hot_probe",
            kwargs={
                "reason": "patrol_idle_fallback",
                "posts_per_source": posts_per_source,
            },
            queue="probe_queue",
        )
    except Exception:
        module_logger.exception("probe hot fallback dispatch failed")
        return False

    return True


async def mark_failure_hit(
    *,
    session_factory: Callable[[], Any],
    community_name: str,
    now: datetime | None = None,
) -> None:
    hit_at = now or datetime.now(timezone.utc)
    async with session_factory() as db:
        await db.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
        await db.execute(
            pg_insert(CommunityCache)
            .values(community_name=community_name, last_crawled_at=hit_at)
            .on_conflict_do_update(
                index_elements=["community_name"],
                set_={
                    "failure_hit": CommunityCache.failure_hit + 1,
                    "last_attempt_at": hit_at,
                },
            )
        )


async def mark_empty_hit(
    *,
    session_factory: Callable[[], Any],
    community_name: str,
    now: datetime | None = None,
) -> None:
    hit_at = now or datetime.now(timezone.utc)
    async with session_factory() as db:
        await db.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
        await db.execute(
            pg_insert(CommunityCache)
            .values(community_name=community_name, last_crawled_at=hit_at)
            .on_conflict_do_update(
                index_elements=["community_name"],
                set_={
                    "empty_hit": CommunityCache.empty_hit + 1,
                    "last_attempt_at": hit_at,
                },
            )
        )


async def list_stale_caches(
    *,
    session_factory: Callable[[], Any],
    threshold_minutes: int = 90,
) -> list[tuple[str, datetime]]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)
    async with session_factory() as session:
        result = await session.execute(
            CommunityCache.__table__.select().where(
                CommunityCache.last_crawled_at < cutoff
            )
        )
        rows = result.fetchall()
        return [
            (row._mapping["community_name"], row._mapping["last_crawled_at"])
            for row in rows
            if row._mapping["last_crawled_at"] is not None
        ]
