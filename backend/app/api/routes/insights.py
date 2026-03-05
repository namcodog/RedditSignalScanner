from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, decode_jwt_token
from app.db.session import get_session
from app.schemas.insight import InsightCardListResponse, InsightCardResponse
from app.services.insight_service import (
    InsightFilters,
    InsightNotFoundError,
    InsightService,
    TaskAccessDeniedError,
    TaskNotFoundError,
)

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get(
    "/{task_id}",
    response_model=InsightCardListResponse,
    summary="获取指定任务的洞察卡片列表",
    description="根据任务 ID 返回结构化洞察卡片，支持置信度和子版块过滤。",
)
async def list_insights_by_task(
    task_id: UUID,
    min_confidence: float | None = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="最小置信度（0-1），用于过滤洞察卡片",
    ),
    subreddit: str | None = Query(
        default=None,
        description="按子版块过滤，支持精确匹配（区分大小写）",
    ),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> InsightCardListResponse:
    service = InsightService(db)
    filters = InsightFilters(
        min_confidence=min_confidence,
        subreddit=subreddit,
        limit=limit,
        offset=offset,
    )

    try:
        return await service.list_by_task(
            task_id=task_id,
            user_id=UUID(payload.sub),
            filters=filters,
        )
    except TaskNotFoundError as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        ) from exc
    except TaskAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to access this task",
        ) from exc


@router.get(
    "/card/{insight_id}",
    response_model=InsightCardResponse,
    summary="获取单个洞察卡片",
    description="根据洞察卡片 ID 获取详细信息",
)
async def get_insight(
    insight_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> InsightCardResponse:
    service = InsightService(db)

    try:
        return await service.get_by_id(
            insight_id=insight_id,
            user_id=UUID(payload.sub),
        )
    except InsightNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight card not found",
        ) from exc
    except TaskAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to access this insight card",
        ) from exc


__all__ = ["router"]
