from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.security import TokenPayload
from app.db.session import get_session
from app.models.facts_snapshot import FactsSnapshot

router = APIRouter(prefix="/admin/facts", tags=["admin"])


def _serialize_snapshot(
    snapshot: FactsSnapshot, *, include_package: bool
) -> dict[str, object]:
    payload: dict[str, object] = {
        "snapshot_id": str(snapshot.id),
        "task_id": str(snapshot.task_id),
        "created_at": snapshot.created_at,
        "schema_version": snapshot.schema_version,
        "tier": snapshot.tier,
        "passed": snapshot.passed,
        "quality": snapshot.quality,
    }
    if include_package:
        payload["v2_package"] = snapshot.v2_package
    return payload


@router.get("/tasks/{task_id}/latest", summary="获取任务最新 facts_v2 审计包")
async def get_latest_facts_snapshot_for_task(
    task_id: uuid.UUID,
    include_package: bool = Query(False),
    payload: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    result = await db.execute(
        select(FactsSnapshot)
        .where(FactsSnapshot.task_id == task_id)
        .order_by(FactsSnapshot.created_at.desc())
        .limit(1)
    )
    snapshot = result.scalars().first()
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Facts snapshot not found")
    return _serialize_snapshot(snapshot, include_package=include_package)


@router.get("/snapshots/{snapshot_id}", summary="获取指定 facts_v2 审计快照")
async def get_facts_snapshot(
    snapshot_id: uuid.UUID,
    include_package: bool = Query(False),
    payload: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    snapshot = await db.get(FactsSnapshot, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Facts snapshot not found")
    return _serialize_snapshot(snapshot, include_package=include_package)

