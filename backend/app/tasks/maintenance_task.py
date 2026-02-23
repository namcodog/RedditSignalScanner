"""
维护任务：数据库清理、备份等

包含:
- refresh_posts_latest: 刷新 posts_latest 物化视图
- cleanup_expired_posts_hot: 清理过期的 posts_hot 数据
- cleanup_expired_facts_audit: 清理过期的 facts 审计包/运行日志
- cleanup_old_posts: 清理超过保留期的 posts_raw 冷数据
- collect_storage_metrics: 采集存储层指标快照
- archive_old_posts: 将历史版本归档至 posts_archive
- check_storage_capacity: 检查数据库容量并预警
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from celery.utils.log import get_task_logger  # type: ignore[import-untyped]
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy import create_engine

from app.core.celery_app import celery_app
from app.db.session import SessionFactory
from app.core.config import get_settings

logger = get_task_logger(__name__)
_MODULE_LOGGER = logging.getLogger(__name__)

DEFAULT_STORAGE_CAPACITY_THRESHOLD_GB = float(
    os.getenv("STORAGE_CAPACITY_THRESHOLD_GB", "50")
)

_MV_REFRESH_PERMISSION_WARNED: set[str] = set()


def _is_mv_permission_error(exc: DBAPIError) -> bool:
    message = str(getattr(exc, "orig", exc)).lower()
    return (
        "must be owner of materialized view" in message
        or "permission denied" in message
        or "must be owner of relation" in message
    )


def _warn_mv_permission_once(view_name: str, exc: DBAPIError) -> None:
    # Phase106: 不让定时任务“刷屏”。权限问题本质是环境/角色配置，先一次性告警即可。
    if view_name in _MV_REFRESH_PERMISSION_WARNED:
        return
    _MV_REFRESH_PERMISSION_WARNED.add(view_name)
    message = str(getattr(exc, "orig", exc))
    logger.warning(
        "Skip refreshing materialized view %s due to permission error: %s",
        view_name,
        message,
    )


def _maintenance_audit_meta(
    task_name: str,
    started_at: datetime,
    affected_rows: int | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = (
        "pytest"
        if os.getenv("PYTEST_CURRENT_TEST")
        else ("celery" if os.getenv("CELERY_WORKER_PID") else "unknown")
    )
    triggered_by = os.getenv("USER") or os.getenv("GITHUB_ACTOR") or "unknown"
    return {
        "task_name": task_name,
        "source": source,
        "triggered_by": triggered_by,
        "started_at": started_at,
        "affected": 0 if affected_rows is None else affected_rows,
        "extra": extra or {},
    }


async def _write_maintenance_audit(
    db,
    *,
    task_name: str,
    started_at: datetime,
    affected_rows: int | None,
    extra: dict[str, Any] | None = None,
) -> None:
    try:
        meta = _maintenance_audit_meta(task_name, started_at, affected_rows, extra)
        extra_payload = json.dumps(meta["extra"])
        await db.execute(
            text(
                """
                INSERT INTO maintenance_audit
                    (task_name, source, triggered_by, started_at, ended_at, affected_rows, sample_ids, extra)
                VALUES
                    (:task_name, :source, :triggered_by, :started_at, NOW(), :affected, :samples, CAST(:extra AS JSONB))
                """
            ),
            {
                "task_name": meta["task_name"],
                "source": meta["source"],
                "triggered_by": meta["triggered_by"],
                "started_at": meta["started_at"],
                "affected": meta["affected"],
                "samples": [],
                "extra": extra_payload,
            },
        )
        await db.commit()
    except Exception:
        _MODULE_LOGGER.exception("Failed to write maintenance_audit record")


def _write_maintenance_audit_sync(
    conn,
    *,
    task_name: str,
    started_at: datetime,
    affected_rows: int | None,
    extra: dict[str, Any] | None = None,
) -> None:
    try:
        meta = _maintenance_audit_meta(task_name, started_at, affected_rows, extra)
        extra_payload = json.dumps(meta["extra"])
        conn.execute(
            text(
                """
                INSERT INTO maintenance_audit
                    (task_name, source, triggered_by, started_at, ended_at, affected_rows, sample_ids, extra)
                VALUES
                    (:task_name, :source, :triggered_by, :started_at, NOW(), :affected, :samples, CAST(:extra AS JSONB))
                """
            ),
            {
                "task_name": meta["task_name"],
                "source": meta["source"],
                "triggered_by": meta["triggered_by"],
                "started_at": meta["started_at"],
                "affected": meta["affected"],
                "samples": [],
                "extra": extra_payload,
            },
        )
    except Exception:
        logger.exception("Failed to write maintenance_audit record (sync)")


def _cleanup_source_component() -> str:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return "pytest"
    if os.getenv("CELERY_WORKER_PID"):
        return "celery"
    if os.getenv("MAKEFLAGS"):
        return "make"
    return "unknown"


async def _enable_safe_delete(db) -> None:
    # Guarded deletes require explicit opt-in per transaction.
    await db.execute(text("SET LOCAL app.allow_delete = '1'"))


async def _write_cleanup_audit(
    db,
    *,
    task_name: str,
    total_records: int,
    breakdown: dict[str, Any],
    duration_seconds: float,
    success: bool = True,
    error_message: str | None = None,
) -> None:
    try:
        breakdown_payload = json.dumps(breakdown)
        await db.execute(
            text(
                """
                INSERT INTO cleanup_logs
                    (total_records_cleaned, breakdown, duration_seconds, success, error_message)
                VALUES
                    (:total, CAST(:breakdown AS JSONB), :duration, :success, :error_message)
                """
            ),
            {
                "total": int(total_records),
                "breakdown": breakdown_payload,
                "duration": int(round(duration_seconds)),
                "success": bool(success),
                "error_message": error_message,
            },
        )
        await db.execute(
            text(
                """
                INSERT INTO data_audit_events
                    (event_type, target_type, target_id, old_value, new_value, reason, source_component)
                VALUES
                    (:event_type, :target_type, :target_id, NULL, CAST(:new_value AS JSONB), :reason, :source_component)
                """
            ),
            {
                "event_type": "cleanup",
                "target_type": "maintenance_task",
                "target_id": task_name,
                "new_value": json.dumps(
                    {
                        "total_records": int(total_records),
                        "breakdown": breakdown,
                        "duration_seconds": duration_seconds,
                        "success": bool(success),
                    }
                ),
                "reason": "maintenance_cleanup",
                "source_component": _cleanup_source_component(),
            },
        )
    except Exception:
        _MODULE_LOGGER.exception("Failed to write cleanup audit records")


def _refresh_view_with_fallback(conn, view_name: str) -> bool:
    try:
        conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}"))
        return True
    except DBAPIError as exc:
        message = str(getattr(exc, "orig", exc))
        if "CONCURRENTLY" in message or "unique index" in message or "not been populated" in message:
            conn.execute(text(f"REFRESH MATERIALIZED VIEW {view_name}"))
            return False
        raise


async def refresh_posts_latest_impl() -> dict[str, Any]:
    """
    刷新 posts_latest 物化视图的实现函数。
    """
    start_time = datetime.now(timezone.utc)

    async with SessionFactory() as db:
        result = await db.execute(
            text("SELECT refresh_posts_latest() AS refreshed_count")
        )
        refreshed_count = int(result.scalar() or 0)
        await _write_maintenance_audit(
            db,
            task_name="refresh_posts_latest",
            started_at=start_time,
            affected_rows=refreshed_count,
            extra={"view": "posts_latest"},
        )

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    _MODULE_LOGGER.info(
        "🔄 posts_latest 物化视图刷新完成: count=%s, duration=%.2fs",
        refreshed_count,
        duration,
    )
    return {
        "status": "completed",
        "refreshed_count": refreshed_count,
        "duration_seconds": duration,
    }


@celery_app.task(name="tasks.maintenance.refresh_posts_latest")  # type: ignore[misc]
def refresh_posts_latest() -> dict[str, Any]:
    """Celery 任务：刷新 posts_latest 物化视图（同步执行，避免 asyncio loop 争用）"""
    settings = get_settings()
    sync_url = settings.database_url
    if sync_url.startswith("postgresql+asyncpg"):
        sync_url = sync_url.replace("postgresql+asyncpg", "postgresql+psycopg")
    elif sync_url.startswith("postgresql+psycopg2"):
        sync_url = sync_url.replace("postgresql+psycopg2", "postgresql+psycopg")
    engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")
    start_time = datetime.now(timezone.utc)
    concurrent: bool | None = None
    skipped_reason: str | None = None
    with engine.begin() as conn:
        try:
            concurrent = _refresh_view_with_fallback(conn, "posts_latest")
        except DBAPIError as exc:
            if _is_mv_permission_error(exc):
                _warn_mv_permission_once("posts_latest", exc)
                skipped_reason = "permission_denied"
            else:
                raise
        _write_maintenance_audit_sync(
            conn,
            task_name="refresh_posts_latest",
            started_at=start_time,
            affected_rows=None,
            extra={
                "view": "posts_latest",
                "concurrent": concurrent,
                "skipped_reason": skipped_reason,
            },
        )
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    payload = {
        "status": "skipped" if skipped_reason else "completed",
        "duration_seconds": duration,
        "skipped_reason": skipped_reason,
    }
    logger.info("✅ 物化视图刷新任务完成: %s", payload)
    return payload


def _refresh_materialized_view(
    *,
    view_name: str,
    task_name: str,
) -> dict[str, Any]:
    settings = get_settings()
    sync_url = settings.database_url
    if sync_url.startswith("postgresql+asyncpg"):
        sync_url = sync_url.replace("postgresql+asyncpg", "postgresql+psycopg")
    elif sync_url.startswith("postgresql+psycopg2"):
        sync_url = sync_url.replace("postgresql+psycopg2", "postgresql+psycopg")
    engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")
    start_time = datetime.now(timezone.utc)
    concurrent: bool | None = None
    skipped_reason: str | None = None
    with engine.begin() as conn:
        try:
            concurrent = _refresh_view_with_fallback(conn, view_name)
        except DBAPIError as exc:
            if _is_mv_permission_error(exc):
                _warn_mv_permission_once(view_name, exc)
                skipped_reason = "permission_denied"
            else:
                raise
        _write_maintenance_audit_sync(
            conn,
            task_name=task_name,
            started_at=start_time,
            affected_rows=None,
            extra={
                "view": view_name,
                "concurrent": concurrent,
                "skipped_reason": skipped_reason,
            },
        )
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    payload = {
        "status": "skipped" if skipped_reason else "completed",
        "duration_seconds": duration,
        "skipped_reason": skipped_reason,
    }
    logger.info("✅ %s 物化视图刷新任务完成: %s", view_name, payload)
    return payload


def _refresh_mining_views() -> dict[str, Any]:
    settings = get_settings()
    sync_url = settings.database_url
    if sync_url.startswith("postgresql+asyncpg"):
        sync_url = sync_url.replace("postgresql+asyncpg", "postgresql+psycopg")
    elif sync_url.startswith("postgresql+psycopg2"):
        sync_url = sync_url.replace("postgresql+psycopg2", "postgresql+psycopg")
    engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")
    start_time = datetime.now(timezone.utc)
    with engine.begin() as conn:
        concurrent_labels: bool | None = None
        concurrent_entities: bool | None = None
        skipped: dict[str, str | None] = {"mv_analysis_labels": None, "mv_analysis_entities": None}
        try:
            concurrent_labels = _refresh_view_with_fallback(conn, "mv_analysis_labels")
        except DBAPIError as exc:
            if _is_mv_permission_error(exc):
                _warn_mv_permission_once("mv_analysis_labels", exc)
                skipped["mv_analysis_labels"] = "permission_denied"
            else:
                raise
        try:
            concurrent_entities = _refresh_view_with_fallback(conn, "mv_analysis_entities")
        except DBAPIError as exc:
            if _is_mv_permission_error(exc):
                _warn_mv_permission_once("mv_analysis_entities", exc)
                skipped["mv_analysis_entities"] = "permission_denied"
            else:
                raise
        _write_maintenance_audit_sync(
            conn,
            task_name="refresh_mining_views",
            started_at=start_time,
            affected_rows=None,
            extra={
                "views": ["mv_analysis_labels", "mv_analysis_entities"],
                "concurrent": {
                    "mv_analysis_labels": concurrent_labels,
                    "mv_analysis_entities": concurrent_entities,
                },
                "skipped_reason": skipped,
            },
        )
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    payload = {"status": "completed", "duration_seconds": duration, "skipped_reason": skipped}
    logger.info("✅ mv_analysis_* 物化视图刷新任务完成: %s", payload)
    return payload


@celery_app.task(name="tasks.maintenance.refresh_mv_monthly_trend")  # type: ignore[misc]
def refresh_mv_monthly_trend() -> dict[str, Any]:
    """Celery 任务：刷新 mv_monthly_trend 物化视图。"""
    return _refresh_materialized_view(
        view_name="mv_monthly_trend",
        task_name="refresh_mv_monthly_trend",
    )


@celery_app.task(name="tasks.maintenance.refresh_post_comment_stats")  # type: ignore[misc]
def refresh_post_comment_stats() -> dict[str, Any]:
    """Celery 任务：刷新 post_comment_stats 物化视图。"""
    return _refresh_materialized_view(
        view_name="post_comment_stats",
        task_name="refresh_post_comment_stats",
    )


@celery_app.task(name="tasks.maintenance.refresh_mining_views")  # type: ignore[misc]
def refresh_mining_views() -> dict[str, Any]:
    """Celery 任务：刷新 mv_analysis_labels / mv_analysis_entities。"""
    return _refresh_mining_views()


async def cleanup_expired_posts_hot_impl() -> dict[str, Any]:
    """
    清理过期的 posts_hot 数据（实现函数）。
    """
    start_time = datetime.now(timezone.utc)

    async with SessionFactory() as db:
        await _enable_safe_delete(db)
        result = await db.execute(
            text("SELECT cleanup_expired_hot_cache() AS deleted_count")
        )
        deleted_count = int(result.scalar() or 0)
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        await _write_cleanup_audit(
            db,
            task_name="cleanup_expired_posts_hot",
            total_records=deleted_count,
            breakdown={"posts_hot": deleted_count},
            duration_seconds=duration,
        )
        await db.commit()
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()

    _MODULE_LOGGER.info(
        "🧹 posts_hot 清理完成: deleted=%s, duration=%.2fs",
        deleted_count,
        duration,
    )

    async with SessionFactory() as db:
        await _write_maintenance_audit(
            db,
            task_name="cleanup_expired_posts_hot",
            started_at=start_time,
            affected_rows=deleted_count,
            extra={"view": "posts_hot"},
        )

    return {
        "status": "completed",
        "deleted_count": deleted_count,
        "duration_seconds": duration,
    }


@celery_app.task(name="tasks.maintenance.cleanup_expired_posts_hot")  # type: ignore[misc]
def cleanup_expired_posts_hot() -> dict[str, Any]:
    """
    Celery 任务: 清理过期的 posts_hot 数据。
    """
    import asyncio
    
    logger.info("🧹 开始执行 posts_hot 清理任务")
    result = asyncio.run(cleanup_expired_posts_hot_impl())
    logger.info(f"✅ 清理任务完成: {result}")
    
    return result


async def cleanup_expired_facts_audit_impl(
    *,
    batch_size: int = 5_000,
    max_batches: int = 100,
    skip_guard: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """清理过期的 facts 审计包与最小运行日志（facts_snapshots / facts_run_logs）。"""
    start_time = datetime.now(timezone.utc)
    enabled_flag = os.getenv("ENABLE_FACTS_AUDIT_CLEANUP", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if not enabled_flag and not skip_guard:
        _MODULE_LOGGER.warning(
            "Facts audit cleanup skipped: ENABLE_FACTS_AUDIT_CLEANUP not set"
        )
        return {
            "status": "skipped",
            "reason": "disabled",
            "deleted_snapshots": 0,
            "deleted_run_logs": 0,
            "batches": 0,
            "duration_seconds": 0.0,
        }

    batch_size = max(1, int(batch_size))
    max_batches = max(1, int(max_batches))

    deleted_snapshots = 0
    deleted_run_logs = 0
    batches = 0

    async with SessionFactory() as db:
        has_snapshots = (
            await db.execute(text("SELECT to_regclass('public.facts_snapshots')"))
        ).scalar_one_or_none() is not None
        has_run_logs = (
            await db.execute(text("SELECT to_regclass('public.facts_run_logs')"))
        ).scalar_one_or_none() is not None

        if not has_snapshots and not has_run_logs:
            return {
                "status": "skipped",
                "reason": "table_missing",
                "deleted_snapshots": 0,
                "deleted_run_logs": 0,
                "batches": 0,
                "duration_seconds": 0.0,
            }

        sample_snapshot_ids: list[str] = []
        sample_run_log_ids: list[str] = []

        if dry_run:
            total_snapshots = 0
            total_run_logs = 0
            if has_snapshots:
                count_row = await db.execute(
                    text(
                        """
                        SELECT COUNT(*)::bigint AS cnt
                        FROM facts_snapshots
                        WHERE expires_at IS NOT NULL AND expires_at < NOW()
                        """
                    )
                )
                total_snapshots = int(count_row.scalar() or 0)
                sample_rows = await db.execute(
                    text(
                        """
                        SELECT id
                        FROM facts_snapshots
                        WHERE expires_at IS NOT NULL AND expires_at < NOW()
                        ORDER BY expires_at
                        LIMIT :limit
                        """
                    ),
                    {"limit": min(50, batch_size)},
                )
                sample_snapshot_ids = [str(r[0]) for r in sample_rows.fetchall()]
            if has_run_logs:
                count_row = await db.execute(
                    text(
                        """
                        SELECT COUNT(*)::bigint AS cnt
                        FROM facts_run_logs
                        WHERE expires_at IS NOT NULL AND expires_at < NOW()
                        """
                    )
                )
                total_run_logs = int(count_row.scalar() or 0)
                sample_rows = await db.execute(
                    text(
                        """
                        SELECT id
                        FROM facts_run_logs
                        WHERE expires_at IS NOT NULL AND expires_at < NOW()
                        ORDER BY expires_at
                        LIMIT :limit
                        """
                    ),
                    {"limit": min(50, batch_size)},
                )
                sample_run_log_ids = [str(r[0]) for r in sample_rows.fetchall()]
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            return {
                "status": "dry_run",
                "total_snapshots": total_snapshots,
                "total_run_logs": total_run_logs,
                "sample_snapshot_ids": sample_snapshot_ids,
                "sample_run_log_ids": sample_run_log_ids,
                "duration_seconds": duration,
            }

        for _ in range(max_batches):
            await _enable_safe_delete(db)
            picked_snapshots = 0
            picked_run_logs = 0
            if has_snapshots:
                row = (
                    await db.execute(
                        text(
                            """
                            WITH victim AS (
                                SELECT id
                                FROM facts_snapshots
                                WHERE expires_at IS NOT NULL AND expires_at < NOW()
                                ORDER BY expires_at
                                LIMIT :limit
                            ),
                            deleted AS (
                                DELETE FROM facts_snapshots
                                WHERE id IN (SELECT id FROM victim)
                                RETURNING 1
                            )
                            SELECT
                                (SELECT COUNT(*) FROM victim) AS picked,
                                (SELECT COUNT(*) FROM deleted) AS deleted
                            """
                        ),
                        {"limit": batch_size},
                    )
                ).mappings().one()
                picked_snapshots = int(row.get("picked") or 0)
                deleted_snapshots += int(row.get("deleted") or 0)
                if not sample_snapshot_ids:
                    sample_rows = await db.execute(
                        text(
                            """
                            SELECT id
                            FROM facts_snapshots
                            WHERE expires_at IS NOT NULL AND expires_at < NOW()
                            ORDER BY expires_at
                            LIMIT :limit
                            """
                        ),
                        {"limit": min(50, batch_size)},
                    )
                    sample_snapshot_ids = [str(r[0]) for r in sample_rows.fetchall()]
            if has_run_logs:
                row = (
                    await db.execute(
                        text(
                            """
                            WITH victim AS (
                                SELECT id
                                FROM facts_run_logs
                                WHERE expires_at IS NOT NULL AND expires_at < NOW()
                                ORDER BY expires_at
                                LIMIT :limit
                            ),
                            deleted AS (
                                DELETE FROM facts_run_logs
                                WHERE id IN (SELECT id FROM victim)
                                RETURNING 1
                            )
                            SELECT
                                (SELECT COUNT(*) FROM victim) AS picked,
                                (SELECT COUNT(*) FROM deleted) AS deleted
                            """
                        ),
                        {"limit": batch_size},
                    )
                ).mappings().one()
                picked_run_logs = int(row.get("picked") or 0)
                deleted_run_logs += int(row.get("deleted") or 0)
                if not sample_run_log_ids:
                    sample_rows = await db.execute(
                        text(
                            """
                            SELECT id
                            FROM facts_run_logs
                            WHERE expires_at IS NOT NULL AND expires_at < NOW()
                            ORDER BY expires_at
                            LIMIT :limit
                            """
                        ),
                        {"limit": min(50, batch_size)},
                    )
                    sample_run_log_ids = [str(r[0]) for r in sample_rows.fetchall()]

            if picked_snapshots == 0 and picked_run_logs == 0:
                break
            batches += 1
            await db.commit()

        # audit record (best-effort)
        try:
            source = (
                "pytest"
                if os.getenv("PYTEST_CURRENT_TEST")
                else ("celery" if os.getenv("CELERY_WORKER_PID") else "unknown")
            )
            triggered_by = (
                os.getenv("USER") or os.getenv("GITHUB_ACTOR") or "unknown"
            )
            await db.execute(
                text(
                    """
                    INSERT INTO maintenance_audit (task_name, source, triggered_by, started_at, ended_at, affected_rows, sample_ids, extra)
                    VALUES (:task_name, :source, :triggered_by, :started_at, NOW(), :affected, :samples, :extra)
                    """
                ),
                {
                    "task_name": "cleanup_expired_facts_audit",
                    "source": source,
                    "triggered_by": triggered_by,
                    "started_at": start_time,
                    "affected": int(deleted_snapshots + deleted_run_logs),
                    "samples": (sample_snapshot_ids + sample_run_log_ids)[:50],
                    "extra": {
                        "deleted_snapshots": int(deleted_snapshots),
                        "deleted_run_logs": int(deleted_run_logs),
                        "batch_size": batch_size,
                        "max_batches": max_batches,
                        "batches": batches,
                    },
                },
            )
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            await _write_cleanup_audit(
                db,
                task_name="cleanup_expired_facts_audit",
                total_records=int(deleted_snapshots + deleted_run_logs),
                breakdown={
                    "facts_snapshots": int(deleted_snapshots),
                    "facts_run_logs": int(deleted_run_logs),
                    "batch_size": batch_size,
                    "batches": batches,
                },
                duration_seconds=duration,
            )
            await db.commit()
        except Exception:
            _MODULE_LOGGER.exception("Failed to write maintenance_audit record")

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    return {
        "status": "completed",
        "deleted_snapshots": int(deleted_snapshots),
        "deleted_run_logs": int(deleted_run_logs),
        "batches": int(batches),
        "duration_seconds": duration,
    }


@celery_app.task(name="tasks.maintenance.cleanup_expired_facts_audit")  # type: ignore[misc]
def cleanup_expired_facts_audit(
    *,
    batch_size: int = 5_000,
    max_batches: int = 100,
    dry_run: bool = False,
) -> dict[str, Any]:
    import asyncio

    logger.info(
        "🧹 开始执行 facts audit 清理任务: batch_size=%s max_batches=%s dry_run=%s",
        batch_size,
        max_batches,
        dry_run,
    )
    result = asyncio.run(
        cleanup_expired_facts_audit_impl(
            batch_size=batch_size, max_batches=max_batches, dry_run=dry_run
        )
    )
    logger.info("✅ facts audit 清理任务完成: %s", result)
    return result


async def cleanup_expired_comments_impl(skip_guard: bool = False) -> dict[str, Any]:
    """清理过期的 comments 以及其关联的 labels/entities。

    安全门：默认需要设置环境变量 ENABLE_COMMENTS_CLEANUP 才会执行；
    测试或受控调用可通过传入 skip_guard=True 跳过该保护。
    """
    start_time = datetime.now(timezone.utc)
    from app.core.config import get_settings
    settings = get_settings()
    # destructive-op guard
    enabled_flag = os.getenv("ENABLE_COMMENTS_CLEANUP", "").strip().lower() in {"1", "true", "yes"}
    if not enabled_flag and not skip_guard:
        _MODULE_LOGGER.warning("Comments cleanup skipped: ENABLE_COMMENTS_CLEANUP not set")
        return {
            "status": "skipped",
            "reason": "disabled",
            "expired_ids": 0,
            "deleted_labels": 0,
            "deleted_entities": 0,
            "deleted_comments": 0,
            "duration_seconds": 0.0,
        }
    try:
        retention_days = int(getattr(settings, "comments_retention_days", 180))
    except Exception:
        retention_days = 180

    async with SessionFactory() as db:
        # collect expired ids first
        # detect if expires_at column exists to maintain compatibility on older DBs
        col_check = await db.execute(
            text(
                "SELECT 1 FROM information_schema.columns WHERE table_name='comments' AND column_name='expires_at'"
            )
        )
        has_expires = col_check.first() is not None

        if has_expires:
            # 优先使用 expires_at；若为空，则回退到 captured_at（不是 Reddit 的 created_utc）
            expired_ids_sql = text(
                """
                SELECT id
                FROM comments
                WHERE (
                    expires_at IS NOT NULL AND expires_at < NOW()
                ) OR (
                    expires_at IS NULL AND captured_at < (NOW() - :days * interval '1 day')
                )
                """
            )
        else:
            # 旧库兼容：无 expires_at 时，使用 captured_at 判断保留期，避免误删历史很久但刚抓到的评论
            expired_ids_sql = text(
                f"""
                SELECT id
                FROM comments
                WHERE captured_at < (NOW() - ({int(retention_days)} * interval '1 day'))
                """
            )
        if has_expires:
            expired_ids_result = await db.execute(expired_ids_sql, {"days": retention_days})
        else:
            expired_ids_result = await db.execute(expired_ids_sql)
        ids = [int(row[0]) for row in expired_ids_result.fetchall()]
        deleted_labels = deleted_entities = deleted_comments = 0
        if ids:
            await _enable_safe_delete(db)
            # delete related labels/entities
            res1 = await db.execute(
                text(
                    "DELETE FROM content_labels WHERE content_type='comment' AND content_id = ANY(:ids) RETURNING 1"
                ),
                {"ids": ids},
            )
            deleted_labels = res1.rowcount or 0
            res2 = await db.execute(
                text(
                    "DELETE FROM content_entities WHERE content_type='comment' AND content_id = ANY(:ids) RETURNING 1"
                ),
                {"ids": ids},
            )
            deleted_entities = res2.rowcount or 0
            res3 = await db.execute(
                text("DELETE FROM comments WHERE id = ANY(:ids) RETURNING 1"),
                {"ids": ids},
            )
            deleted_comments = res3.rowcount or 0
        # write audit record
        try:
            from sqlalchemy import text as _t
            source = (
                "pytest" if os.getenv("PYTEST_CURRENT_TEST") else (
                    "make" if os.getenv("MAKEFLAGS") else (
                        "celery" if os.getenv("CELERY_WORKER_PID") else "unknown"
                    )
                )
            )
            triggered_by = os.getenv("USER") or os.getenv("GITHUB_ACTOR") or os.getenv("CI_PIPELINE_SOURCE") or "unknown"
            await db.execute(
                _t(
                    """
                    INSERT INTO maintenance_audit (task_name, source, triggered_by, started_at, ended_at, affected_rows, sample_ids, extra)
                    VALUES (:task_name, :source, :triggered_by, :started_at, NOW(), :affected, :samples, :extra)
                    """
                ),
                {
                    "task_name": "cleanup_expired_comments",
                    "source": source,
                    "triggered_by": triggered_by,
                    "started_at": start_time,
                    "affected": int(deleted_comments or 0),
                    "samples": ids[:50],
                    "extra": {
                        "retention_days": retention_days,
                        "has_expires": has_expires,
                    },
                },
            )
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            await _write_cleanup_audit(
                db,
                task_name="cleanup_expired_comments",
                total_records=int(deleted_labels + deleted_entities + deleted_comments),
                breakdown={
                    "comments": int(deleted_comments),
                    "content_labels": int(deleted_labels),
                    "content_entities": int(deleted_entities),
                    "retention_days": retention_days,
                    "expired_ids": len(ids),
                },
                duration_seconds=duration,
            )
        except Exception:
            _MODULE_LOGGER.exception("Failed to write maintenance_audit record")

        await db.commit()

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    _MODULE_LOGGER.info(
        "🧹 comments 清理完成: expired_ids=%s, labels=%s, entities=%s, comments=%s, duration=%.2fs",
        len(ids),
        deleted_labels,
        deleted_entities,
        deleted_comments,
        duration,
    )
    return {
        "status": "completed",
        "expired_ids": len(ids),
        "deleted_labels": deleted_labels,
        "deleted_entities": deleted_entities,
        "deleted_comments": deleted_comments,
        "duration_seconds": duration,
    }


@celery_app.task(name="tasks.maintenance.cleanup_expired_comments")  # type: ignore[misc]
def cleanup_expired_comments() -> dict[str, Any]:
    import asyncio

    logger.info("🧹 开始执行 comments 清理任务")
    result = asyncio.run(cleanup_expired_comments_impl())
    logger.info("✅ comments 清理任务完成: %s", result)
    return result


async def cleanup_noise_comments_impl(
    *,
    batch_size: int = 5_000,
    max_batches: int = 200,
    expired_only: bool = True,
    dry_run: bool = False,
    skip_guard: bool = False,
) -> dict[str, Any]:
    """分批清理 noise 的 comments（并清掉对应 labels/entities）。

    目标原则（业务不被影响）：
    - 只删 noise，不动 core/lab
    - 默认只清“已过期”的 noise（更稳）；如需清全量 noise，可把 expired_only=False

    安全门：
    - 默认需要设置环境变量 ENABLE_COMMENTS_NOISE_CLEANUP 才会执行；
      测试或受控调用可通过传入 skip_guard=True 跳过该保护。
    """
    start_time = datetime.now(timezone.utc)
    enabled_flag = (
        os.getenv("ENABLE_COMMENTS_NOISE_CLEANUP", "").strip().lower()
        in {"1", "true", "yes"}
    )
    if not enabled_flag and not skip_guard:
        _MODULE_LOGGER.warning(
            "Noise comments cleanup skipped: ENABLE_COMMENTS_NOISE_CLEANUP not set"
        )
        return {
            "status": "skipped",
            "reason": "disabled",
            "deleted_comments": 0,
            "deleted_labels": 0,
            "deleted_entities": 0,
            "batches": 0,
            "duration_seconds": 0.0,
        }

    batch_size = max(1, int(batch_size))
    max_batches = max(1, int(max_batches))

    try:
        settings = get_settings()
        retention_days = int(getattr(settings, "comments_retention_days", 180))
    except Exception:
        retention_days = 180

    deleted_comments = deleted_labels = deleted_entities = 0
    batches = 0

    async with SessionFactory() as db:
        # detect if expires_at exists (older DB compat)
        has_expires = (
            await db.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='comments' AND column_name='expires_at' "
                    "LIMIT 1"
                )
            )
        ).first() is not None

        has_business_pool = (
            await db.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='comments' AND column_name='business_pool' "
                    "LIMIT 1"
                )
            )
        ).first() is not None

        # Safety principle: treat the current persisted business_pool as the source of truth.
        # Do NOT delete lab/core rows even if scoring marked them as noise.
        join_scores = ""
        noise_predicate = (
            "COALESCE(c.business_pool, 'lab') = 'noise'" if has_business_pool else "FALSE"
        )
        expiry_predicate = ""
        needs_retention_days = bool(expired_only and not has_expires)
        params: dict[str, Any] = {"limit": batch_size}
        if needs_retention_days:
            params["retention_days"] = retention_days
        if expired_only:
            if has_expires:
                expiry_predicate = "AND c.expires_at IS NOT NULL AND c.expires_at < NOW()"
            else:
                expiry_predicate = "AND c.captured_at < (NOW() - :retention_days * interval '1 day')"

        if dry_run:
            # cheap preview: count + sample ids (bounded)
            count_row = await db.execute(
                text(
                    f"""
                    SELECT COUNT(*)::bigint AS cnt
                    FROM comments c
                    {join_scores}
                    WHERE {noise_predicate}
                    {expiry_predicate}
                    """
                ),
                {"retention_days": retention_days} if needs_retention_days else {},
            )
            total = int(count_row.scalar() or 0)
            sample_rows = await db.execute(
                text(
                    f"""
                    SELECT c.id
                    FROM comments c
                    {join_scores}
                    WHERE {noise_predicate}
                    {expiry_predicate}
                    ORDER BY c.id
                    LIMIT :limit
                    """
                ),
                params,
            )
            sample_ids = [int(r[0]) for r in sample_rows.fetchall()]
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            return {
                "status": "dry_run",
                "expired_only": bool(expired_only),
                "has_expires": bool(has_expires),
                "has_business_pool": bool(has_business_pool),
                "total_candidates": total,
                "sample_ids": sample_ids,
                "duration_seconds": duration,
            }

        for _ in range(max_batches):
            await _enable_safe_delete(db)
            stmt = text(
                f"""
                WITH victim AS (
                    SELECT c.id
                    FROM comments c
                    {join_scores}
                    WHERE {noise_predicate}
                    {expiry_predicate}
                    ORDER BY c.id
                    LIMIT :limit
                ),
                del_labels AS (
                    DELETE FROM content_labels cl
                    USING victim v
                    WHERE cl.content_type='comment' AND cl.content_id=v.id
                    RETURNING 1
                ),
                del_entities AS (
                    DELETE FROM content_entities ce
                    USING victim v
                    WHERE ce.content_type='comment' AND ce.content_id=v.id
                    RETURNING 1
                ),
                del_comments AS (
                    DELETE FROM comments c
                    USING victim v
                    WHERE c.id=v.id
                    RETURNING 1
                )
                SELECT
                    (SELECT COUNT(*) FROM victim) AS picked,
                    (SELECT COUNT(*) FROM del_labels) AS deleted_labels,
                    (SELECT COUNT(*) FROM del_entities) AS deleted_entities,
                    (SELECT COUNT(*) FROM del_comments) AS deleted_comments
                """
            )
            row = (await db.execute(stmt, params)).mappings().one()
            picked = int(row.get("picked") or 0)
            if picked <= 0:
                break
            deleted_labels += int(row.get("deleted_labels") or 0)
            deleted_entities += int(row.get("deleted_entities") or 0)
            deleted_comments += int(row.get("deleted_comments") or 0)
            batches += 1
            await db.commit()

        # audit record (best-effort)
        try:
            source = (
                "pytest"
                if os.getenv("PYTEST_CURRENT_TEST")
                else ("celery" if os.getenv("CELERY_WORKER_PID") else "unknown")
            )
            triggered_by = os.getenv("USER") or os.getenv("GITHUB_ACTOR") or "unknown"
            await db.execute(
                text(
                    """
                    INSERT INTO maintenance_audit (task_name, source, triggered_by, started_at, ended_at, affected_rows, sample_ids, extra)
                    VALUES (:task_name, :source, :triggered_by, :started_at, NOW(), :affected, :samples, :extra)
                    """
                ),
                {
                    "task_name": "cleanup_noise_comments",
                    "source": source,
                    "triggered_by": triggered_by,
                    "started_at": start_time,
                    "affected": int(deleted_comments or 0),
                    "samples": [],
                    "extra": {
                        "expired_only": bool(expired_only),
                        "has_expires": bool(has_expires),
                        "has_business_pool": bool(has_business_pool),
                        "batch_size": batch_size,
                        "max_batches": max_batches,
                        "batches": batches,
                    },
                },
            )
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            await _write_cleanup_audit(
                db,
                task_name="cleanup_noise_comments",
                total_records=int(deleted_comments + deleted_labels + deleted_entities),
                breakdown={
                    "comments": int(deleted_comments),
                    "content_labels": int(deleted_labels),
                    "content_entities": int(deleted_entities),
                    "expired_only": bool(expired_only),
                    "batch_size": batch_size,
                    "batches": batches,
                },
                duration_seconds=duration,
            )
            await db.commit()
        except Exception:
            _MODULE_LOGGER.exception("Failed to write maintenance_audit record")

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    return {
        "status": "completed",
        "expired_only": bool(expired_only),
        "deleted_comments": int(deleted_comments or 0),
        "deleted_labels": int(deleted_labels or 0),
        "deleted_entities": int(deleted_entities or 0),
        "batches": int(batches or 0),
        "duration_seconds": duration,
    }


@celery_app.task(name="tasks.maintenance.cleanup_noise_comments")  # type: ignore[misc]
def cleanup_noise_comments(
    *,
    batch_size: int = 5_000,
    max_batches: int = 200,
    expired_only: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    import asyncio

    logger.info(
        "🧹 开始执行 noise comments 清理任务: batch_size=%s max_batches=%s expired_only=%s dry_run=%s",
        batch_size,
        max_batches,
        expired_only,
        dry_run,
    )
    result = asyncio.run(
        cleanup_noise_comments_impl(
            batch_size=batch_size,
            max_batches=max_batches,
            expired_only=expired_only,
            dry_run=dry_run,
        )
    )
    logger.info("✅ noise comments 清理任务完成: %s", result)
    return result


async def cleanup_orphan_content_labels_entities_impl(
    *,
    batch_size: int = 5_000,
    max_batches: int = 200,
    lock_timeout_ms: int = 1_000,
    statement_timeout_s: int = 60,
    start_after_label_id: int = 0,
    start_after_entity_id: int = 0,
) -> dict[str, Any]:
    """Batch cleanup orphan content_labels/content_entities rows."""
    start_time = datetime.now(timezone.utc)
    deleted_labels = 0
    deleted_entities = 0
    batches = 0
    last_label_id = max(start_after_label_id, 0)
    last_entity_id = max(start_after_entity_id, 0)
    lock_timeout = f"{max(lock_timeout_ms, 0)}ms"
    statement_timeout = f"{max(statement_timeout_s, 1)}s"

    table_configs = [
        ("content_labels", "labels"),
        ("content_entities", "entities"),
    ]

    async with SessionFactory() as db:
        for table_name, label in table_configs:
            last_id = last_label_id if label == "labels" else last_entity_id
            while batches < max_batches:
                batch_start = datetime.now(timezone.utc)
                await db.execute(text(f"SET LOCAL lock_timeout = '{lock_timeout}'"))
                await db.execute(text(f"SET LOCAL statement_timeout = '{statement_timeout}'"))
                await _enable_safe_delete(db)
                res = await db.execute(
                    text(
                        f"""
                        WITH victims AS (
                            SELECT id, content_type
                            FROM {table_name}
                            WHERE id > :last_id
                              AND (
                                (content_type = 'post'
                                 AND NOT EXISTS (
                                     SELECT 1 FROM posts_hot WHERE id = {table_name}.content_id
                                 ))
                                OR
                                (content_type = 'comment'
                                 AND NOT EXISTS (
                                     SELECT 1 FROM comments WHERE id = {table_name}.content_id
                                 ))
                              )
                            ORDER BY id
                            LIMIT :limit
                        )
                        DELETE FROM {table_name}
                        WHERE id IN (SELECT id FROM victims)
                        RETURNING id, content_type
                        """
                    ),
                    {"last_id": last_id, "limit": batch_size},
                )
                rows = res.fetchall()
                if not rows:
                    await db.commit()
                    break

                batch_deleted = len(rows)
                post_deleted = sum(1 for row in rows if row.content_type == "post")
                comment_deleted = batch_deleted - post_deleted
                last_id = max(row.id for row in rows)
                if label == "labels":
                    deleted_labels += batch_deleted
                    last_label_id = last_id
                else:
                    deleted_entities += batch_deleted
                    last_entity_id = last_id

                batches += 1
                duration = (datetime.now(timezone.utc) - batch_start).total_seconds()
                await _write_cleanup_audit(
                    db,
                    task_name="cleanup_orphan_content_labels_entities",
                    total_records=batch_deleted,
                    breakdown={
                        "table": table_name,
                        "batch": batches,
                        "deleted_total": batch_deleted,
                        "deleted_posts": post_deleted,
                        "deleted_comments": comment_deleted,
                        "batch_size": batch_size,
                        "last_id": last_id,
                        "lock_timeout_ms": lock_timeout_ms,
                        "statement_timeout_s": statement_timeout_s,
                    },
                    duration_seconds=duration,
                )
                await db.commit()

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    payload = {
        "status": "completed",
        "deleted_labels": int(deleted_labels),
        "deleted_entities": int(deleted_entities),
        "batches": int(batches),
        "last_label_id": int(last_label_id),
        "last_entity_id": int(last_entity_id),
        "duration_seconds": duration,
    }
    _MODULE_LOGGER.info("🧹 orphan labels/entities batch cleanup done: %s", payload)
    return payload


@celery_app.task(name="tasks.maintenance.cleanup_orphan_content_labels_entities")  # type: ignore[misc]
def cleanup_orphan_content_labels_entities(
    *,
    batch_size: int = 5_000,
    max_batches: int = 200,
    lock_timeout_ms: int = 1_000,
    statement_timeout_s: int = 60,
    start_after_label_id: int = 0,
    start_after_entity_id: int = 0,
) -> dict[str, Any]:
    import asyncio

    logger.info(
        "🧹 开始执行 orphan content_labels/content_entities 清理任务: "
        "batch_size=%s max_batches=%s lock_timeout_ms=%s statement_timeout_s=%s "
        "start_after_label_id=%s start_after_entity_id=%s",
        batch_size,
        max_batches,
        lock_timeout_ms,
        statement_timeout_s,
        start_after_label_id,
        start_after_entity_id,
    )
    result = asyncio.run(
        cleanup_orphan_content_labels_entities_impl(
            batch_size=batch_size,
            max_batches=max_batches,
            lock_timeout_ms=lock_timeout_ms,
            statement_timeout_s=statement_timeout_s,
            start_after_label_id=start_after_label_id,
            start_after_entity_id=start_after_entity_id,
        )
    )
    logger.info("✅ orphan content_labels/content_entities 清理任务完成: %s", result)
    return result


async def collect_storage_metrics_impl() -> dict[str, Any]:
    """采集并写入 storage_metrics 表的实现函数。"""
    start_time = datetime.now(timezone.utc)

    async with SessionFactory() as db:
        metrics_result = await db.execute(text("SELECT metric, value FROM get_storage_stats()"))
        stats = {row.metric: int(row.value) for row in metrics_result}

        posts_raw_total = stats.get("posts_raw_total", 0)
        posts_raw_current = stats.get("posts_raw_current", 0)
        posts_hot_total = stats.get("posts_hot_total", 0)
        posts_hot_expired = stats.get("posts_hot_expired", 0)
        unique_subreddits = stats.get("unique_subreddits", 0)
        total_versions = stats.get("total_versions", 0)

        duplicates = posts_raw_total - posts_raw_current
        dedup_rate = duplicates / posts_raw_total if posts_raw_total else 0.0

        insert_result = await db.execute(
            text(
                """
                INSERT INTO storage_metrics (
                    posts_raw_total,
                    posts_raw_current,
                    posts_hot_total,
                    posts_hot_expired,
                    unique_subreddits,
                    total_versions,
                    dedup_rate
                )
                VALUES (
                    :posts_raw_total,
                    :posts_raw_current,
                    :posts_hot_total,
                    :posts_hot_expired,
                    :unique_subreddits,
                    :total_versions,
                    :dedup_rate
                )
                RETURNING id, collected_at
                """
            ),
            {
                "posts_raw_total": posts_raw_total,
                "posts_raw_current": posts_raw_current,
                "posts_hot_total": posts_hot_total,
                "posts_hot_expired": posts_hot_expired,
                "unique_subreddits": unique_subreddits,
                "total_versions": total_versions,
                "dedup_rate": round(dedup_rate, 6),
            },
        )
        inserted = insert_result.one()
        await db.commit()

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    snapshot = {
        "status": "completed",
        "id": int(inserted.id),
        "collected_at": inserted.collected_at.isoformat(),
        "posts_raw_total": posts_raw_total,
        "posts_raw_current": posts_raw_current,
        "posts_hot_total": posts_hot_total,
        "posts_hot_expired": posts_hot_expired,
        "unique_subreddits": unique_subreddits,
        "total_versions": total_versions,
        "dedup_rate": round(dedup_rate, 6),
        "duration_seconds": duration,
    }
    _MODULE_LOGGER.info("📊 存储指标采集完成: %s", snapshot)
    return snapshot


@celery_app.task(name="tasks.maintenance.collect_storage_metrics")  # type: ignore[misc]
def collect_storage_metrics() -> dict[str, Any]:
    """Celery 任务：采集存储层质量指标。"""
    import asyncio

    logger.info("📊 开始采集存储层指标")
    result = asyncio.run(collect_storage_metrics_impl())
    logger.info("✅ 存储层指标采集完成: %s", result)
    return result


async def cleanup_soft_orphan_content_labels_entities_impl(
    *,
    retention_days: int = 30,
    batch_size: int = 5_000,
    max_batches: int = 200,
    lock_timeout_ms: int = 1_000,
    statement_timeout_s: int = 60,
    start_after_label_id: int = 0,
    start_after_entity_id: int = 0,
) -> dict[str, Any]:
    """Batch cleanup soft orphan labels/entities with a retention window."""
    start_time = datetime.now(timezone.utc)
    deleted_labels = 0
    deleted_entities = 0
    batches = 0
    last_label_id = max(start_after_label_id, 0)
    last_entity_id = max(start_after_entity_id, 0)
    lock_timeout = f"{max(lock_timeout_ms, 0)}ms"
    statement_timeout = f"{max(statement_timeout_s, 1)}s"
    retention_days = max(0, int(retention_days))

    table_configs = [
        ("content_labels", "labels"),
        ("content_entities", "entities"),
    ]

    async with SessionFactory() as db:
        for table_name, label in table_configs:
            last_id = last_label_id if label == "labels" else last_entity_id
            while batches < max_batches:
                batch_start = datetime.now(timezone.utc)
                await db.execute(text(f"SET LOCAL lock_timeout = '{lock_timeout}'"))
                await db.execute(text(f"SET LOCAL statement_timeout = '{statement_timeout}'"))
                await _enable_safe_delete(db)
                res = await db.execute(
                    text(
                        f"""
                        WITH victims AS (
                            SELECT t.id, t.content_type
                            FROM {table_name} t
                            LEFT JOIN posts_hot ph
                                ON t.content_type = 'post' AND ph.id = t.content_id
                            LEFT JOIN comments c
                                ON t.content_type = 'comment' AND c.id = t.content_id
                            WHERE t.id > :last_id
                              AND t.created_at < (NOW() - (:retention_days * interval '1 day'))
                              AND (
                                (t.content_type = 'post'
                                 AND ph.id IS NOT NULL
                                 AND ph.expires_at < (NOW() - (:retention_days * interval '1 day')))
                                OR
                                (t.content_type = 'comment'
                                 AND c.id IS NOT NULL
                                 AND c.removed_by_category IS NOT NULL)
                              )
                            ORDER BY t.id
                            LIMIT :limit
                        )
                        DELETE FROM {table_name}
                        WHERE id IN (SELECT id FROM victims)
                        RETURNING id, content_type
                        """
                    ),
                    {
                        "last_id": last_id,
                        "limit": batch_size,
                        "retention_days": retention_days,
                    },
                )
                rows = res.fetchall()
                if not rows:
                    await db.commit()
                    break

                batch_deleted = len(rows)
                post_deleted = sum(1 for row in rows if row.content_type == "post")
                comment_deleted = batch_deleted - post_deleted
                last_id = max(row.id for row in rows)
                if label == "labels":
                    deleted_labels += batch_deleted
                    last_label_id = last_id
                else:
                    deleted_entities += batch_deleted
                    last_entity_id = last_id

                batches += 1
                duration = (datetime.now(timezone.utc) - batch_start).total_seconds()
                await _write_cleanup_audit(
                    db,
                    task_name="cleanup_soft_orphan_content_labels_entities",
                    total_records=batch_deleted,
                    breakdown={
                        "table": table_name,
                        "batch": batches,
                        "deleted_total": batch_deleted,
                        "deleted_posts": post_deleted,
                        "deleted_comments": comment_deleted,
                        "batch_size": batch_size,
                        "last_id": last_id,
                        "retention_days": retention_days,
                        "lock_timeout_ms": lock_timeout_ms,
                        "statement_timeout_s": statement_timeout_s,
                    },
                    duration_seconds=duration,
                )
                await db.commit()

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    payload = {
        "status": "completed",
        "deleted_labels": int(deleted_labels),
        "deleted_entities": int(deleted_entities),
        "batches": int(batches),
        "last_label_id": int(last_label_id),
        "last_entity_id": int(last_entity_id),
        "duration_seconds": duration,
    }
    _MODULE_LOGGER.info("🧹 soft orphan cleanup done: %s", payload)
    return payload


@celery_app.task(name="tasks.maintenance.cleanup_soft_orphan_content_labels_entities")  # type: ignore[misc]
def cleanup_soft_orphan_content_labels_entities(
    *,
    retention_days: int = 30,
    batch_size: int = 5_000,
    max_batches: int = 200,
    lock_timeout_ms: int = 1_000,
    statement_timeout_s: int = 60,
    start_after_label_id: int = 0,
    start_after_entity_id: int = 0,
) -> dict[str, Any]:
    import asyncio

    logger.info(
        "🧹 start soft orphan cleanup: retention_days=%s batch_size=%s max_batches=%s "
        "lock_timeout_ms=%s statement_timeout_s=%s start_after_label_id=%s start_after_entity_id=%s",
        retention_days,
        batch_size,
        max_batches,
        lock_timeout_ms,
        statement_timeout_s,
        start_after_label_id,
        start_after_entity_id,
    )
    result = asyncio.run(
        cleanup_soft_orphan_content_labels_entities_impl(
            retention_days=retention_days,
            batch_size=batch_size,
            max_batches=max_batches,
            lock_timeout_ms=lock_timeout_ms,
            statement_timeout_s=statement_timeout_s,
            start_after_label_id=start_after_label_id,
            start_after_entity_id=start_after_entity_id,
        )
    )
    logger.info("✅ soft orphan cleanup done: %s", result)
    return result


async def cleanup_old_posts_impl(retention_days: int = 90) -> dict[str, Any]:
    """
    清理 posts_raw 中超过保留期的历史数据。
    """
    start_time = datetime.now(timezone.utc)

    async with SessionFactory() as db:
        await _enable_safe_delete(db)
        result = await db.execute(
            text("SELECT cleanup_old_posts(:retention_days) AS deleted_count"),
            {"retention_days": retention_days},
        )
        deleted_count = int(result.scalar() or 0)
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        await _write_cleanup_audit(
            db,
            task_name="cleanup_old_posts",
            total_records=deleted_count,
            breakdown={"posts_raw": deleted_count, "retention_days": retention_days},
            duration_seconds=duration,
        )
        await db.commit()

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    _MODULE_LOGGER.info(
        "🧊 posts_raw 冷库清理完成: retention=%s, deleted=%s, duration=%.2fs",
        retention_days,
        deleted_count,
        duration,
    )

    async with SessionFactory() as db:
        await _write_maintenance_audit(
            db,
            task_name="cleanup_old_posts",
            started_at=start_time,
            affected_rows=deleted_count,
            extra={"retention_days": retention_days},
        )

    return {
        "status": "completed",
        "retention_days": retention_days,
        "deleted_count": deleted_count,
        "duration_seconds": duration,
    }


@celery_app.task(name="tasks.maintenance.cleanup_old_posts")  # type: ignore[misc]
def cleanup_old_posts(retention_days: int = 90) -> dict[str, Any]:
    """
    Celery 任务：清理超过保留期的 posts_raw 冷数据。
    """
    import asyncio

    logger.info("🧊 开始执行 posts_raw 冷库清理任务 (retention=%s 天)", retention_days)
    result = asyncio.run(cleanup_old_posts_impl(retention_days=retention_days))
    logger.info("✅ 冷库清理任务完成: %s", result)
    return result


async def archive_old_posts_impl(
    retention_days: int = 90, batch_size: int = 1000
) -> dict[str, Any]:
    """将历史版本归档至 posts_archive。"""
    start_time = datetime.now(timezone.utc)

    async with SessionFactory() as db:
        result = await db.execute(
            text(
                "SELECT archive_old_posts(:retention_days, :batch_size) AS archived_count"
            ),
            {"retention_days": retention_days, "batch_size": batch_size},
        )
        await db.commit()

    archived_count = int(result.scalar() or 0)
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    payload = {
        "status": "completed",
        "retention_days": retention_days,
        "batch_size": batch_size,
        "archived_count": archived_count,
        "duration_seconds": duration,
    }
    _MODULE_LOGGER.info("🗄️ 归档任务完成: %s", payload)
    return payload


@celery_app.task(name="tasks.maintenance.archive_old_posts")  # type: ignore[misc]
def archive_old_posts(retention_days: int = 90, batch_size: int = 1000) -> dict[str, Any]:
    """Celery 任务：归档历史版本数据。"""
    import asyncio

    logger.info(
        "🗄️ 开始执行 posts_raw 归档任务 (retention=%s, batch=%s)",
        retention_days,
        batch_size,
    )
    result = asyncio.run(
        archive_old_posts_impl(retention_days=retention_days, batch_size=batch_size)
    )
    logger.info("✅ 归档任务完成: %s", result)
    return result


async def check_storage_capacity_impl(
    threshold_gb: float | None = None,
) -> dict[str, Any]:
    """检查数据库容量并返回评估结果。"""
    threshold = (
        threshold_gb
        if threshold_gb is not None
        else DEFAULT_STORAGE_CAPACITY_THRESHOLD_GB
    )

    async with SessionFactory() as db:
        result = await db.execute(
            text(
                """
                SELECT
                    pg_database_size(current_database()) AS database_size,
                    pg_total_relation_size('posts_raw'::regclass) AS posts_raw_size,
                    pg_total_relation_size('posts_hot'::regclass) AS posts_hot_size
                """
            )
        )
        row = result.one()

    database_size_gb = row.database_size / 1024**3
    posts_raw_size_gb = row.posts_raw_size / 1024**3
    posts_hot_size_gb = row.posts_hot_size / 1024**3
    above_threshold = database_size_gb >= threshold

    payload = {
        "status": "alert" if above_threshold else "ok",
        "database_size_gb": round(database_size_gb, 3),
        "posts_raw_size_gb": round(posts_raw_size_gb, 3),
        "posts_hot_size_gb": round(posts_hot_size_gb, 3),
        "threshold_gb": threshold,
    }

    if above_threshold:
        _MODULE_LOGGER.warning("⚠️ 数据库容量接近阈值: %s", payload)
    else:
        _MODULE_LOGGER.info("📦 数据库容量检查通过: %s", payload)
    return payload


@celery_app.task(name="tasks.maintenance.check_storage_capacity")  # type: ignore[misc]
def check_storage_capacity(threshold_gb: float | None = None) -> dict[str, Any]:
    """Celery 任务：检查数据库容量并输出预警。"""
    import asyncio

    result = asyncio.run(check_storage_capacity_impl(threshold_gb=threshold_gb))
    logger.info("📦 存储容量检查结果: %s", result)
    return result
