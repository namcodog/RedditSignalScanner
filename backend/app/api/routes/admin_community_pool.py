from __future__ import annotations

import uuid
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.admin import _response
from app.core.auth import require_admin
from app.core.security import TokenPayload
from app.db.session import get_session
from app.models.community_pool import CommunityPool, PendingCommunity

router = APIRouter(prefix="/admin/communities", tags=["admin"])  # mounted under /api
logger = logging.getLogger(__name__)


def safe_int(value: Any) -> int:
    """Convert values to int while preserving logging hook for tests."""
    return int(value)


class ApproveRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    tier: str = Field("medium", min_length=3, max_length=20)
    categories: Dict[str, Any] | None = None
    admin_notes: Optional[str] = None


class RejectRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    admin_notes: Optional[str] = None


@router.get("/pool", summary="查看社区池")
async def list_community_pool(
    session: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    stmt = (
        select(CommunityPool)
        .where(CommunityPool.deleted_at.is_(None))
        .order_by(CommunityPool.name.asc())
    )
    result = await session.execute(stmt)
    items = result.scalars().all()

    data = {
        "items": [
            {
                "name": c.name,
                "tier": c.tier,
                "categories": c.categories,
                "description_keywords": c.description_keywords,
                "daily_posts": c.daily_posts,
                "avg_comment_length": c.avg_comment_length,
                "quality_score": float(c.quality_score),
                "priority": c.priority,
                "user_feedback_count": c.user_feedback_count,
                "discovered_count": c.discovered_count,
                "is_active": c.is_active,
            }
            for c in items
        ],
        "total": len(items),
    }
    return _response(data)


@router.get("/discovered", summary="查看待审核社区")
async def list_discovered(
    session: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    stmt = (
        select(PendingCommunity)
        .where(
            PendingCommunity.status == "pending",
            PendingCommunity.deleted_at.is_(None),
        )
        .order_by(PendingCommunity.last_discovered_at.desc())
    )
    result = await session.execute(stmt)
    items = result.scalars().all()

    data = {
        "items": [
            {
                "name": p.name,
                "discovered_from_keywords": p.discovered_from_keywords,
                "discovered_count": p.discovered_count,
                "first_discovered_at": p.first_discovered_at,
                "last_discovered_at": p.last_discovered_at,
                "status": p.status,
            }
            for p in items
        ],
        "total": len(items),
    }
    return _response(data)


@router.post("/approve", summary="批准社区")
async def approve_community(
    body: ApproveRequest,
    session: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    # Find pending record
    pending = await session.scalar(
        select(PendingCommunity).where(PendingCommunity.name == body.name)
    )
    if pending is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pending community not found"
        )

    # Upsert into CommunityPool
    pool = await session.scalar(
        select(CommunityPool).where(CommunityPool.name == body.name)
    )
    now = datetime.now(timezone.utc)

    try:
        reviewer_id = uuid.UUID(payload.sub)
    except (ValueError, TypeError) as exc:
        logger.warning("管理员令牌 subject 无法解析: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        )

    if pool is None:
        description_keywords = pending.discovered_from_keywords or {"keywords": []}
        categories = body.categories or {"source": "discovered"}
        pool = CommunityPool(
            name=body.name,
            tier=body.tier,
            categories=categories,
            description_keywords=description_keywords,
            daily_posts=0,
            avg_comment_length=0,
            quality_score=0.50,
            priority="medium",
            user_feedback_count=0,
            discovered_count=pending.discovered_count,
            is_active=True,
            created_by=reviewer_id,
            updated_by=reviewer_id,
        )
        session.add(pool)
    else:
        pool.is_active = True
        pool.deleted_at = None
        pool.deleted_by = None
        pool.updated_by = reviewer_id
        try:
            pool.discovered_count = safe_int(pool.discovered_count) + safe_int(
                pending.discovered_count
            )
        except Exception as exc:
            logger.warning(
                "无法累加 discovered_count，使用待审核值覆盖: %s", exc,
            )
            pool.discovered_count = safe_int(pending.discovered_count)

    # Update pending state
    pending.status = "approved"
    pending.admin_reviewed_at = now
    pending.reviewed_by = reviewer_id
    pending.admin_notes = body.admin_notes
    pending.updated_by = reviewer_id

    await session.commit()

    return _response({"approved": body.name, "pool_is_active": True})


@router.post("/reject", summary="拒绝社区")
async def reject_community(
    body: RejectRequest,
    session: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    pending = await session.scalar(
        select(PendingCommunity).where(PendingCommunity.name == body.name)
    )
    if pending is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pending community not found"
        )

    try:
        reviewer_id = uuid.UUID(payload.sub)
    except (ValueError, TypeError) as exc:
        logger.warning("管理员令牌 subject 无法解析: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        )

    now = datetime.now(timezone.utc)
    pending.status = "rejected"
    pending.admin_reviewed_at = now
    pending.reviewed_by = reviewer_id
    pending.admin_notes = body.admin_notes
    pending.updated_by = reviewer_id

    await session.commit()
    return _response({"rejected": body.name})


@router.delete("/{name:path}", summary="禁用社区")
async def disable_community(
    name: str = Path(..., min_length=2, max_length=200),
    session: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    pool = await session.scalar(
        select(CommunityPool).where(CommunityPool.name == name)
    )
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Community not found"
        )

    try:
        actor_id = uuid.UUID(payload.sub)
    except (ValueError, TypeError) as exc:
        logger.warning("管理员令牌 subject 无法解析: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        )

    pool.is_active = False
    pool.deleted_at = datetime.now(timezone.utc)
    pool.deleted_by = actor_id
    pool.updated_by = actor_id
    await session.commit()

    return _response({"disabled": name})


__all__ = ["router"]
