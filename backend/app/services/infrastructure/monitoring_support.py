from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Mapping

from sqlalchemy import text

from app.schemas import monitoring as monitoring_schemas
from app.services.community.community_pool_loader import CommunityPoolLoader
from app.services.ops import contract_health as contract_health_ops


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def mark_payload_degraded(
    payload: Dict[str, Any] | monitoring_schemas.MonitoringTaskResult,
    *,
    code: str,
    message: str,
) -> None:
    if isinstance(payload, monitoring_schemas.MonitoringTaskResult):
        payload.degraded_checks.append(
            monitoring_schemas.MonitoringDegradedCheck(code=code, message=message)
        )
        if payload.status not in {"error", "degraded"}:
            payload.status = "degraded"
        return

    degraded_checks = payload.setdefault("degraded_checks", [])
    if isinstance(degraded_checks, list):
        degraded_checks.append({"code": code, "message": message})
    if payload.get("status") not in {"error", "degraded"}:
        payload["status"] = "degraded"


def build_monitoring_error_result(
    *, message: str, generated_at: datetime | None = None
) -> dict[str, Any]:
    return monitoring_schemas.MonitoringTaskResult(
        status="error",
        generated_at=generated_at or utc_now(),
        message=message,
    ).model_dump(mode="json")


def serialize_monitoring_result(
    result: monitoring_schemas.MonitoringTaskResult | dict[str, Any]
) -> dict[str, Any]:
    if isinstance(result, dict):
        return result
    return result.model_dump(mode="json")


async def load_cache_seed_names() -> list[str]:
    from app.db.session import SessionFactory

    async with SessionFactory() as db:
        loader = CommunityPoolLoader(db)
        communities = await loader.load_community_pool(force_refresh=False)
    return [profile.name for profile in communities if profile.tier.lower() == "seed"]


async def load_entity_extraction_metrics(*, cutoff: datetime) -> Dict[str, Any]:
    from app.db.session import SessionFactory

    async with SessionFactory() as db_metrics:
        res_posts = await db_metrics.execute(
            text("SELECT count(*) FROM posts_hot WHERE created_at >= :cutoff"),
            {"cutoff": cutoff},
        )
        res_entities = await db_metrics.execute(
            text(
                """
                SELECT count(*)
                FROM semantic_observation
                WHERE observation_type = 'content_entity'
                  AND observed_at >= :cutoff
                """
            ),
            {"cutoff": cutoff},
        )
    recent_posts = int(res_posts.scalar() or 0)
    recent_entities = int(res_entities.scalar() or 0)
    entity_rate = recent_entities / recent_posts if recent_posts > 0 else None
    return {
        "entity_rate": entity_rate,
        "recent_posts": recent_posts,
        "recent_entities": recent_entities,
    }


async def run_cache_maintenance_tasks() -> Dict[str, Dict[str, Any] | None]:
    from app.tasks import maintenance_task

    cleanup, metrics_snapshot = await asyncio.gather(
        maintenance_task.cleanup_expired_posts_hot_impl(),
        maintenance_task.collect_storage_metrics_impl(),
    )
    return {
        "cleanup": cleanup,
        "metrics_snapshot": metrics_snapshot,
    }


def build_contract_health_thresholds(
    *, as_float: Any, as_int: Any
) -> contract_health_ops.ContractHealthAlertThresholds:
    return contract_health_ops.ContractHealthAlertThresholds(
        comments_not_used_rate_warn=as_float(
            os.getenv("CONTRACT_HEALTH_ALERT_COMMENTS_NOT_USED_RATE_WARN", "0.10"),
            default=0.10,
        ),
        x_blocked_rate_warn=as_float(
            os.getenv("CONTRACT_HEALTH_ALERT_X_BLOCKED_RATE_WARN", "0.15"),
            default=0.15,
        ),
        data_validation_error_count_warn=as_int(
            os.getenv("CONTRACT_HEALTH_ALERT_DATA_VALIDATION_ERROR_COUNT_WARN", "1"),
            default=1,
        ),
    )


def serialize_contract_alerts(
    alerts: list[contract_health_ops.ContractHealthAlert],
) -> list[monitoring_schemas.MonitoringAlertPayload]:
    return [
        monitoring_schemas.MonitoringAlertPayload(
            level=alert.level,
            code=alert.code,
            message=alert.message,
            details=dict(alert.details),
        )
        for alert in alerts
    ]


async def write_contract_health_audit_events(
    payload: Mapping[str, Any], alerts_raw: list[dict[str, Any]]
) -> None:
    from app.db.session import SessionFactory

    async with SessionFactory() as session:
        for raw in alerts_raw[:20]:
            if not isinstance(raw, dict):
                continue
            code = str(raw.get("code") or "unknown")
            await session.execute(
                text(
                    """
                    INSERT INTO data_audit_events (
                        event_type, target_type, target_id, reason, source_component, new_value
                    )
                    VALUES (
                        'monitor', 'system', 'contract_health', :reason, 'monitor_contract_health',
                        CAST(:payload AS JSONB)
                    )
                    """
                ),
                {
                    "reason": code,
                    "payload": json.dumps(
                        {
                            "generated_at": payload.get("generated_at"),
                            "window_hours": payload.get("window_hours"),
                            "alert": raw,
                        },
                        ensure_ascii=False,
                    ),
                },
            )
        await session.commit()


__all__ = [
    "build_contract_health_thresholds",
    "build_monitoring_error_result",
    "load_cache_seed_names",
    "load_entity_extraction_metrics",
    "mark_payload_degraded",
    "run_cache_maintenance_tasks",
    "serialize_monitoring_result",
    "serialize_contract_alerts",
    "utc_now",
    "write_contract_health_audit_events",
]
