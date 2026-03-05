from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Float, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.security import TokenPayload
from app.core.celery_app import celery_app
from app.db.session import get_session
from app.models import Analysis, Task, TaskStatus, User
from app.models.example_library import ExampleLibrary
from app.models.report import Report
from app.schemas.example_library import ExampleLibraryCreate
from app.api.routes.guidance import infer_guidance_tags

router = APIRouter(prefix="/admin", tags=["admin"])


def _response(data: Any) -> dict[str, Any]:
    return {"code": 0, "data": data, "trace_id": uuid.uuid4().hex}


def _calculate_processing_seconds(task: Task) -> float | None:
    if task.started_at is None or task.completed_at is None:
        return None
    delta = task.completed_at - task.started_at
    return float(round(delta.total_seconds(), 2))


def _collect_worker_count() -> int:
    inspect = celery_app.control.inspect()
    if inspect is None:
        return 0

    active = inspect.active() or {}
    return len(active)


@router.get("/dashboard/stats", summary="Admin dashboard aggregate metrics")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    total_users = await db.scalar(select(func.count(User.id))) or 0
    total_tasks = await db.scalar(select(func.count(Task.id))) or 0
    tasks_today = (
        await db.scalar(
            select(func.count(Task.id)).where(Task.created_at >= today_start)
        )
    ) or 0
    tasks_completed_today = (
        await db.scalar(
            select(func.count(Task.id)).where(
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at.is_not(None),
                Task.completed_at >= today_start,
            )
        )
    ) or 0

    processing_avg_seconds = await db.scalar(
        select(
            func.avg(func.extract("epoch", Task.completed_at - Task.started_at))
        ).where(Task.completed_at.is_not(None), Task.started_at.is_not(None))
    )

    avg_processing_time = round(float(processing_avg_seconds or 0.0), 2)

    cache_hit_avg = await db.scalar(
        select(func.avg(Analysis.sources["cache_hit_rate"].astext.cast(Float)))
    )
    cache_hit_rate = round(float(cache_hit_avg or 0.0), 2)

    stats = {
        "total_users": int(total_users),
        "total_tasks": int(total_tasks),
        "tasks_today": int(tasks_today),
        "tasks_completed_today": int(tasks_completed_today),
        "avg_processing_time": avg_processing_time,
        "cache_hit_rate": cache_hit_rate,
        "active_workers": _collect_worker_count(),
        "pipeline_health": {},  # Placeholder for future pipeline health metrics
    }

    return _response(stats)


@router.get("/tasks/recent", summary="Recent tasks overview")
async def get_recent_tasks(
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    base_query = (
        select(Task, User.email, Analysis)
        .join(User, User.id == Task.user_id)
        .outerjoin(Analysis, Analysis.task_id == Task.id)
        .order_by(desc(Task.created_at))
    )

    total_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = int(total_result.scalar() or 0)

    stmt = base_query.limit(limit).offset(offset)
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for task, email, analysis in rows:
        item = {
            "task_id": task.id,
            "user_email": email,
            "status": task.status.value
            if isinstance(task.status, TaskStatus)
            else task.status,
            "created_at": task.created_at,
            "completed_at": task.completed_at,
            "processing_seconds": _calculate_processing_seconds(task),
        }

        # 添加算法评分数据
        if analysis is not None:
            item["confidence_score"] = float(analysis.confidence_score) if analysis.confidence_score else None
            item["analysis_version"] = analysis.analysis_version

            # 从 sources 中提取关键指标
            sources = analysis.sources or {}
            item["posts_analyzed"] = sources.get("posts_analyzed", 0)
            item["cache_hit_rate"] = sources.get("cache_hit_rate", 0.0)
            item["communities_count"] = len(sources.get("communities", []))
            item["reddit_api_calls"] = sources.get("reddit_api_calls", 0)

            # 从 insights 中提取关键指标
            insights = analysis.insights or {}
            item["pain_points_count"] = len(insights.get("pain_points", []))
            item["competitors_count"] = len(insights.get("competitors", []))
            item["opportunities_count"] = len(insights.get("opportunities", []))
        else:
            item["confidence_score"] = None
            item["analysis_version"] = None
            item["posts_analyzed"] = 0
            item["cache_hit_rate"] = 0.0
            item["communities_count"] = 0
            item["reddit_api_calls"] = 0
            item["pain_points_count"] = 0
            item["competitors_count"] = 0
            item["opportunities_count"] = 0

        items.append(item)

    return _response({"items": items, "total": total})


@router.get("/users/active", summary="Active users ranked by recent tasks")
async def get_active_users(
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    threshold = datetime.now(timezone.utc) - timedelta(days=7)

    stmt = (
        select(
            User.id,
            User.email,
            func.count(Task.id).label("task_count"),
            func.max(Task.created_at).label("last_task_at"),
        )
        .join(Task, Task.user_id == User.id)
        .where(Task.created_at >= threshold)
        .group_by(User.id, User.email)
        .order_by(desc("task_count"), desc("last_task_at"))
    )

    total_result = await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )
    total = int(total_result.scalar() or 0)

    result = await db.execute(stmt.limit(limit).offset(offset))
    rows = result.all()
    items = [
        {
            "user_id": row.id,
            "email": row.email,
            "tasks_last_7_days": int(row.task_count),
            "last_task_at": row.last_task_at,
        }
        for row in rows
    ]
    return _response({"items": items, "total": total})


@router.get("/examples", summary="List example library entries")
async def list_example_library(
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    base_query = select(ExampleLibrary).order_by(desc(ExampleLibrary.updated_at))
    total_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = int(total_result.scalar() or 0)

    result = await db.execute(base_query.limit(limit).offset(offset))
    rows = result.scalars().all()
    items = [
        {
            "example_id": row.id,
            "title": row.title,
            "prompt": row.prompt,
            "tags": row.tags,
            "is_active": row.is_active,
            "source_task_id": row.source_task_id,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]
    return _response({"items": items, "total": total})


@router.post("/examples", summary="Promote a task report into the example library")
async def promote_example_library(
    request: ExampleLibraryCreate,
    db: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    task = await db.get(Task, request.task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # 临时切换 RLS 到任务所属用户，确保能读取 analyses/report
    await db.execute(
        text("SELECT set_config('app.current_user_id', :uid, true)"),
        {"uid": str(task.user_id)},
    )

    analysis = await db.scalar(select(Analysis).where(Analysis.task_id == task.id))
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Analysis not found")

    report = await db.scalar(select(Report).where(Report.analysis_id == analysis.id))
    if report is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Report not found")

    sources = analysis.sources or {}
    if "report_structured" not in sources:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="report_structured missing in analysis sources",
        )

    tags = list(request.tags) if request.tags else infer_guidance_tags(task.product_description)
    title = (request.title or (tags[0] if tags else "示例")).strip()

    existing = await db.scalar(
        select(ExampleLibrary).where(ExampleLibrary.source_task_id == task.id)
    )
    if existing is None:
        example = ExampleLibrary(
            title=title,
            prompt=task.product_description,
            tags=tags,
            analysis_insights=analysis.insights,
            analysis_sources=analysis.sources,
            analysis_action_items=analysis.action_items,
            analysis_confidence_score=analysis.confidence_score,
            analysis_version=analysis.analysis_version,
            report_html=report.html_content,
            report_template_version=report.template_version,
            source_task_id=task.id,
            is_active=request.is_active,
            created_by=uuid.UUID(payload.sub),
            updated_by=uuid.UUID(payload.sub),
        )
        db.add(example)
        await db.commit()
        await db.refresh(example)
    else:
        existing.title = title
        existing.prompt = task.product_description
        existing.tags = tags
        existing.analysis_insights = analysis.insights
        existing.analysis_sources = analysis.sources
        existing.analysis_action_items = analysis.action_items
        existing.analysis_confidence_score = analysis.confidence_score
        existing.analysis_version = analysis.analysis_version
        existing.report_html = report.html_content
        existing.report_template_version = report.template_version
        existing.is_active = request.is_active
        existing.updated_by = uuid.UUID(payload.sub)
        await db.commit()
        await db.refresh(existing)
        example = existing

    return _response(
        {
            "example_id": example.id,
            "title": example.title,
            "prompt": example.prompt,
            "tags": example.tags,
            "is_active": example.is_active,
            "source_task_id": example.source_task_id,
        }
    )


@router.delete("/examples/{example_id}", summary="Deactivate an example library entry")
async def deactivate_example_library(
    example_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    example = await db.get(ExampleLibrary, example_id)
    if example is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Example not found")

    example.is_active = False
    example.updated_by = uuid.UUID(payload.sub)
    await db.commit()
    return _response({"example_id": example.id, "is_active": example.is_active})


__all__ = ["router"]
