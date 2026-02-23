from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.security import TokenPayload
from app.db.session import get_session
from app.models import Analysis, Task
from app.models.facts_snapshot import FactsSnapshot

router = APIRouter(prefix="/admin/tasks", tags=["admin"])


def _dt(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


@router.get(
    "/{task_id}/ledger",
    summary="Admin 任务复盘（sources 账本 + facts_v2 审计包索引）",
)
async def get_task_ledger(
    task_id: UUID,
    include_package: bool = Query(False, description="是否返回完整 facts_v2 v2_package（可能很大）"),
    payload: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    task: Task | None = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    analysis: Analysis | None = None
    result = await db.execute(select(Analysis).where(Analysis.task_id == task_id))
    analysis = result.scalars().first()

    snapshot: FactsSnapshot | None = None
    snap_result = await db.execute(
        select(FactsSnapshot)
        .where(FactsSnapshot.task_id == task_id)
        .order_by(desc(FactsSnapshot.created_at))
        .limit(1)
    )
    snapshot = snap_result.scalars().first()

    facts_snapshot_obj: dict[str, object] | None = None
    if snapshot is not None:
        facts_snapshot_obj = {
            "id": str(snapshot.id),
            "task_id": str(snapshot.task_id),
            "schema_version": snapshot.schema_version,
            "tier": snapshot.tier,
            "passed": bool(snapshot.passed),
            "audit_level": snapshot.audit_level,
            "status": snapshot.status,
            "validator_level": snapshot.validator_level,
            "retention_days": snapshot.retention_days,
            "expires_at": _dt(snapshot.expires_at),
            "blocked_reason": snapshot.blocked_reason,
            "error_code": snapshot.error_code,
            "quality": snapshot.quality,
            "created_at": _dt(snapshot.created_at),
        }
        if include_package:
            facts_snapshot_obj["v2_package"] = snapshot.v2_package

    return {
        "task": {
            "id": str(task.id),
            "user_id": str(task.user_id),
            "status": task.status.value,
            "mode": getattr(task, "mode", None),
            "audit_level": getattr(task, "audit_level", None),
            "topic_profile_id": getattr(task, "topic_profile_id", None),
            "product_description": task.product_description,
            "retry_count": task.retry_count,
            "failure_category": task.failure_category,
            "created_at": _dt(task.created_at),
            "updated_at": _dt(task.updated_at),
            "completed_at": _dt(task.completed_at),
        },
        "analysis": (
            {
                "id": str(analysis.id),
                "task_id": str(analysis.task_id),
                "analysis_version": int(analysis.analysis_version),
                "confidence_score": str(analysis.confidence_score)
                if analysis.confidence_score is not None
                else None,
                "sources": analysis.sources,
                "created_at": _dt(analysis.created_at),
            }
            if analysis is not None
            else None
        ),
        "facts_snapshot": facts_snapshot_obj,
    }


__all__ = ["router"]

