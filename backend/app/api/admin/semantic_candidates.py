from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import require_admin
from app.core.security import TokenPayload
from app.db.session import SessionFactory, get_session
from app.models.semantic_candidate import SemanticCandidate
from app.repositories.semantic_candidate_repository import SemanticCandidateRepository
from app.repositories.semantic_term_repository import SemanticTermRepository
from app.services.semantic.audit_logger import SemanticAuditLogger
from app.events.semantic_bus import get_event_bus, Events
from app.services.semantic.provider_factory import get_semantic_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/semantic-candidates", tags=["admin"])


def _response(data: Any) -> dict[str, Any]:
    return {"code": 0, "data": data, "trace_id": uuid.uuid4().hex}


class SemanticCandidateResponse(BaseModel):
    id: int
    term: str
    frequency: int
    source: str
    first_seen_at: datetime
    status: str

    model_config = {"from_attributes": True}


class CandidateStatisticsResponse(BaseModel):
    total: int
    pending: int
    approved: int
    rejected: int
    this_week_new: int


class ApproveCandidateRequest(BaseModel):
    category: str = Field(..., description="brands|features|pain_points")
    layer: str = Field(..., description="L1|L2|L3|L4")
    aliases: List[str] | None = None
    weight: float | None = Field(None, ge=0)


class RejectCandidateRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


async def get_semantic_candidate_repository(
    session: AsyncSession = Depends(get_session),
) -> SemanticCandidateRepository:
    term_repo = SemanticTermRepository(session)
    return SemanticCandidateRepository(session, term_repo)


async def get_semantic_audit_logger(
    session: AsyncSession = Depends(get_session),
) -> SemanticAuditLogger:
    return SemanticAuditLogger(session)


async def get_semantic_provider_dep():
    return get_semantic_provider()

@router.get("", summary="List semantic candidates")
async def list_semantic_candidates(
    status: str = Query("pending", description="pending|approved|rejected"),
    limit: int = Query(100, ge=1, le=500),
    repo: SemanticCandidateRepository = Depends(get_semantic_candidate_repository),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    if not isinstance(status, str):
        status = str(getattr(status, "default", "pending") or "pending")
    # 查询参数在直接调用时可能仍是 fastapi Query 对象，需手工提取默认值
    if not isinstance(limit, int):
        try:
            limit = int(getattr(limit, "default", 100))
        except Exception:
            limit = 100
    if status == "pending":
        candidates = await repo.get_pending(limit=limit)
    else:
        stmt = (
            select(SemanticCandidate)
            .where(SemanticCandidate.status == status)
            .order_by(SemanticCandidate.frequency.desc())
            .limit(limit)
        )
        result = await repo._session.execute(stmt)
        candidates = list(result.scalars().all())

    items = [
        SemanticCandidateResponse.model_validate(c).model_dump() for c in candidates
    ]
    return _response({"items": items, "total": len(items)})


@router.get("/statistics", summary="Semantic candidate statistics")
async def get_semantic_candidate_statistics(
    repo: SemanticCandidateRepository = Depends(get_semantic_candidate_repository),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    stats = await repo.get_statistics()
    response = CandidateStatisticsResponse(**stats)
    return _response(response.model_dump())


def _validate_category_layer(category: str, layer: str) -> None:
    allowed_categories = {"brands", "features", "pain_points"}
    allowed_layers = {"L1", "L2", "L3", "L4"}
    if category not in allowed_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category",
        )
    if layer not in allowed_layers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid layer",
        )


def _ensure_operator_id(payload: TokenPayload) -> uuid.UUID:
    try:
        return uuid.UUID(payload.sub)
    except (ValueError, TypeError) as exc:
        logger.warning("管理员令牌 subject 无法解析: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        ) from exc


@router.post("/{candidate_id}/approve", summary="Approve semantic candidate")
async def approve_semantic_candidate(
    candidate_id: int = Path(..., ge=1),
    body: ApproveCandidateRequest | None = None,
    repo: SemanticCandidateRepository = Depends(get_semantic_candidate_repository),
    audit_logger: SemanticAuditLogger = Depends(get_semantic_audit_logger),
    semantic_provider=Depends(get_semantic_provider_dep),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    if body is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body is required",
        )
    _validate_category_layer(body.category, body.layer)
    operator_id = _ensure_operator_id(payload)

    try:
        term = await repo.approve(
            candidate_id=candidate_id,
            category=body.category,
            layer=body.layer,
            operator_id=operator_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
        ) from None

    updates: Dict[str, Any] = {}
    if body.aliases is not None:
        updates["aliases"] = body.aliases
    if body.weight is not None:
        updates["weight"] = body.weight
    if updates:
        term = await repo.update(term.id, updates)

    await audit_logger.log_approve(
        candidate_id=candidate_id,
        operator_id=operator_id,
        category=body.category,
        layer=body.layer,
    )
    await repo._session.commit()

    try:
        bus = get_event_bus()
        await bus.publish(Events.CANDIDATE_APPROVED, {"candidate_id": candidate_id, "term_id": term.id})
        await bus.publish(Events.LEXICON_UPDATED, {"term_id": term.id, "action": "insert"})
        try:
            await semantic_provider.reload()
        except Exception:
            logger.exception("SemanticProvider reload failed after candidate approval")
    except Exception:
        logger.exception("Event publish failed after candidate approval")

    return _response(
        {
            "id": term.id,
            "canonical": term.canonical,
            "aliases": term.aliases or [],
            "category": term.category,
            "layer": term.layer,
            "precision_tag": term.precision_tag,
            "weight": float(term.weight) if term.weight is not None else None,
            "polarity": term.polarity,
            "lifecycle": term.lifecycle,
        }
    )


@router.post("/{candidate_id}/reject", summary="Reject semantic candidate")
async def reject_semantic_candidate(
    candidate_id: int = Path(..., ge=1),
    body: RejectCandidateRequest | None = None,
    repo: SemanticCandidateRepository = Depends(get_semantic_candidate_repository),
    audit_logger: SemanticAuditLogger = Depends(get_semantic_audit_logger),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    if body is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body is required",
        )
    operator_id = _ensure_operator_id(payload)

    existing = await repo._session.execute(
        select(SemanticCandidate).where(SemanticCandidate.id == candidate_id)
    )
    candidate = existing.scalars().first()
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
        )

    await repo.reject(candidate_id=candidate_id, reason=body.reason, operator_id=operator_id)
    await audit_logger.log_reject(
        candidate_id=candidate_id,
        operator_id=operator_id,
        reason=body.reason,
    )
    await repo._session.commit()

    return _response({"rejected": candidate_id})


__all__ = ["router"]
