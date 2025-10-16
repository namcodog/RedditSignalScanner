from __future__ import annotations

from typing import Any, Dict
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, decode_jwt_token
from app.db.session import get_session
from app.models.beta_feedback import BetaFeedback
from app.models.task import Task
from app.schemas.beta_feedback import BetaFeedbackCreate, BetaFeedbackResponse

router = APIRouter(prefix="/beta", tags=["beta"])


def _response(data: Any) -> Dict[str, Any]:
    return {"code": 0, "data": data, "trace_id": str(uuid.uuid4())}


@router.post("/feedback", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)  # type: ignore[misc]
async def submit_beta_feedback(
    payload: BetaFeedbackCreate,
    db: AsyncSession = Depends(get_session),
    token: TokenPayload = Depends(decode_jwt_token),
) -> Dict[str, Any]:
    """Submit beta tester feedback (PRD-09 Day 17-18).

    Requires authentication. Validates that the task exists and belongs to the user.
    """
    user_id = uuid.UUID(token.sub)

    # Verify task exists and belongs to user
    task = await db.get(Task, payload.task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Task does not belong to user")

    # Create feedback
    feedback = BetaFeedback(
        task_id=payload.task_id,
        user_id=user_id,
        satisfaction=payload.satisfaction,
        missing_communities=payload.missing_communities,
        comments=payload.comments,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    return _response(BetaFeedbackResponse.model_validate(feedback).model_dump())


__all__ = ["router"]

