from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.schemas.monitoring import ContractHealthResult
from app.services.infrastructure.monitoring_support import (
    mark_payload_degraded,
    serialize_contract_alerts,
    serialize_monitoring_result,
)
from app.services.ops.contract_health import (
    ContractHealthAlertThresholds,
    ContractHealthRow,
    compute_contract_health,
    evaluate_contract_health_alerts,
)

_LOGGER = logging.getLogger(__name__)


async def load_contract_health_rows(
    *, cutoff: datetime, now: datetime
) -> list[ContractHealthRow]:
    from app.db.session import SessionFactory
    from app.models.analysis import Analysis
    from app.models.task import Task as TaskModel

    async with SessionFactory() as session:
        result = await session.execute(
            select(
                TaskModel.id,
                TaskModel.status,
                TaskModel.created_at,
                TaskModel.started_at,
                TaskModel.completed_at,
                TaskModel.failure_category,
                Analysis.sources,
            )
            .outerjoin(Analysis, Analysis.task_id == TaskModel.id)
            .where(TaskModel.created_at >= cutoff)
        )
        rows: list[ContractHealthRow] = []
        for (
            task_id,
            status,
            created_at,
            started_at,
            completed_at,
            failure_category,
            sources,
        ) in result.all():
            created = created_at or now
            status_value = getattr(status, "value", status)
            rows.append(
                ContractHealthRow(
                    task_id=str(task_id),
                    status=str(status_value),
                    created_at=created,
                    started_at=started_at,
                    completed_at=completed_at,
                    failure_category=str(failure_category)
                    if failure_category
                    else None,
                    sources=dict(sources) if isinstance(sources, dict) else None,
                )
            )
    return rows


async def build_contract_health_result(
    *,
    window_hours: int,
    now: datetime,
    window: timedelta,
    cutoff: datetime,
    thresholds: ContractHealthAlertThresholds,
) -> ContractHealthResult:
    rows = await load_contract_health_rows(cutoff=cutoff, now=now)
    report = compute_contract_health(rows=rows, now=now, window=window)
    alerts = evaluate_contract_health_alerts(report, thresholds=thresholds)
    return ContractHealthResult(
        status="ok",
        generated_at=now,
        window_hours=window_hours,
        report=report,
        alerts=serialize_contract_alerts(alerts),
    )


def finalize_contract_health_result(
    result: ContractHealthResult,
    *,
    settings: Any,
    update_dashboard: Callable[[Any, dict[str, Any]], None],
    send_alert: Callable[[str, str], None],
    write_audit_events: Callable[[dict[str, Any], list[dict[str, Any]]], None],
) -> ContractHealthResult:
    try:
        update_dashboard(settings, {"contract_health": serialize_monitoring_result(result)})
    except Exception as exc:  # pragma: no cover - defensive
        _LOGGER.warning("contract_health dashboard 写入失败: %s", exc, exc_info=True)
        mark_payload_degraded(
            result,
            code="dashboard_update_failed",
            message=str(exc),
        )

    alerts_raw = [alert.model_dump(mode="json") for alert in result.alerts]
    if alerts_raw:
        for raw in alerts_raw[:20]:
            level = str(raw.get("level") or "warning")
            code = str(raw.get("code") or "unknown")
            message = str(raw.get("message") or "")
            send_alert(level, f"contract_health[{code}]: {message}")
        try:
            write_audit_events(serialize_monitoring_result(result), alerts_raw)
        except Exception as exc:  # pragma: no cover - defensive
            _LOGGER.warning(
                "contract_health audit event 写入失败: %s",
                exc,
                exc_info=True,
            )
            mark_payload_degraded(
                result,
                code="audit_event_write_failed",
                message=str(exc),
            )
    return result


__all__ = [
    "build_contract_health_result",
    "finalize_contract_health_result",
    "load_contract_health_rows",
]
