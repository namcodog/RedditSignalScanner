from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.security import TokenPayload, decode_jwt_token
from app.db.session import get_session
from app.models.insight import Evidence, InsightCard
from app.models.task import Task
from app.schemas.insights import (
    EvidenceResponse,
    InsightCardListResponse,
    InsightCardResponse,
)

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get(
    "",
    response_model=InsightCardListResponse,
    summary="获取洞察卡片列表",
    description="根据任务 ID 或实体过滤器获取洞察卡片列表",
)
async def get_insights(
    task_id: UUID | None = Query(None, description="任务 ID"),
    entity_filter: str | None = Query(None, description="实体过滤器（暂未实现）"),
    min_confidence: float | None = Query(
        None,
        ge=0.0,
        le=1.0,
        description="最小置信度（0-1），用于过滤洞察卡片",
    ),
    subreddit: str | None = Query(
        None,
        description="按子版块过滤，支持精确匹配（区分大小写）",
    ),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> InsightCardListResponse:
    """
    获取洞察卡片列表。
    
    参数：
    - task_id: 可选，按任务 ID 过滤
    - entity_filter: 可选，按实体过滤（暂未实现）
    - limit: 每页数量（1-100）
    - offset: 偏移量
    
    返回：
    - total: 总数
    - items: 洞察卡片列表
    """
    
    # 构建查询
    query = select(InsightCard).options(
        joinedload(InsightCard.evidences),
        joinedload(InsightCard.task),
    )
    
    # 如果指定了 task_id，验证任务所有权并过滤
    count_query = select(func.count(InsightCard.id))

    if task_id is not None:
        # 验证任务所有权
        task = await db.get(Task, task_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )
        if str(task.user_id) != payload.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorised to access this task",
            )
        
        query = query.where(InsightCard.task_id == task_id)
        count_query = count_query.where(InsightCard.task_id == task_id)
    else:
        # 如果没有指定 task_id，只返回当前用户的洞察卡片
        # 通过 JOIN task 表来过滤
        query = query.join(Task).where(Task.user_id == UUID(payload.sub))
        count_query = count_query.join(Task).where(Task.user_id == UUID(payload.sub))

    if min_confidence is not None:
        query = query.where(InsightCard.confidence >= min_confidence)
        count_query = count_query.where(InsightCard.confidence >= min_confidence)

    if subreddit is not None and subreddit.strip():
        normalized = subreddit.strip()
        query = query.where(InsightCard.subreddits.contains([normalized]))
        count_query = count_query.where(InsightCard.subreddits.contains([normalized]))

    # 获取总数
    result = await db.execute(count_query)
    total = int(result.scalar_one() or 0)
    
    # 分页查询
    query = query.order_by(InsightCard.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    insight_cards = result.scalars().unique().all()
    
    # 转换为响应格式
    items = [
        InsightCardResponse(
            id=card.id,
            task_id=card.task_id,
            title=card.title,
            summary=card.summary,
            confidence=float(card.confidence),
            time_window_days=card.time_window_days,
            subreddits=card.subreddits,
            evidences=[
                EvidenceResponse(
                    id=evidence.id,
                    post_url=evidence.post_url,
                    excerpt=evidence.excerpt,
                    timestamp=evidence.timestamp,
                    subreddit=evidence.subreddit,
                    score=float(evidence.score),
                )
                for evidence in card.evidences
            ],
            created_at=card.created_at,
            updated_at=card.updated_at,
        )
        for card in insight_cards
    ]
    
    return InsightCardListResponse(total=total, items=items)


@router.get(
    "/{insight_id}",
    response_model=InsightCardResponse,
    summary="获取单个洞察卡片",
    description="根据洞察卡片 ID 获取详细信息",
)
async def get_insight(
    insight_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> InsightCardResponse:
    """
    获取单个洞察卡片的详细信息。
    
    参数：
    - insight_id: 洞察卡片 ID
    
    返回：
    - 洞察卡片详细信息
    """
    
    # 查询洞察卡片
    query = (
        select(InsightCard)
        .options(
            joinedload(InsightCard.evidences),
            joinedload(InsightCard.task),
        )
        .where(InsightCard.id == insight_id)
    )

    result = await db.execute(query)
    card = result.unique().scalar_one_or_none()
    
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight card not found",
        )
    
    # 验证任务所有权
    if str(card.task.user_id) != payload.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to access this insight card",
        )
    
    # 转换为响应格式
    return InsightCardResponse(
        id=card.id,
        task_id=card.task_id,
        title=card.title,
        summary=card.summary,
        confidence=float(card.confidence),
        time_window_days=card.time_window_days,
        subreddits=card.subreddits,
        evidences=[
            EvidenceResponse(
                id=evidence.id,
                post_url=evidence.post_url,
                excerpt=evidence.excerpt,
                timestamp=evidence.timestamp,
                subreddit=evidence.subreddit,
                score=float(evidence.score),
            )
            for evidence in card.evidences
        ],
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


__all__ = ["router"]
