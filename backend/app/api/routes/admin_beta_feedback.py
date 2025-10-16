from __future__ import annotations

from typing import Any, Dict, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.admin import _response
from app.core.auth import require_admin
from app.core.security import TokenPayload
from app.db.session import get_session
from app.models.beta_feedback import BetaFeedback

router = APIRouter(prefix="/admin/beta", tags=["admin"])  # mounted under /api


@router.get("/feedback", summary="List beta feedback")  # type: ignore[misc]
async def list_beta_feedback(
    _payload: "TokenPayload" = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    stmt = select(BetaFeedback).order_by(BetaFeedback.created_at.desc())
    result = await session.execute(stmt)
    items = result.scalars().all()

    data = {
        "items": [
            {
                "id": str(fb.id),
                "task_id": str(fb.task_id),
                "user_id": str(fb.user_id),
                "satisfaction": fb.satisfaction,
                "missing_communities": fb.missing_communities,
                "comments": fb.comments,
                "created_at": fb.created_at.isoformat(),
            }
            for fb in items
        ],
        "total": len(items),
    }
    return cast(Dict[str, Any], _response(data))


__all__ = ["router"]
