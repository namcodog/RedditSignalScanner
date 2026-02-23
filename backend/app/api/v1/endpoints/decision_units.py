from __future__ import annotations

import uuid
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, decode_jwt_token
from app.db.session import get_session
from app.schemas.decision_unit import (
    DecisionUnitDetail,
    DecisionUnitEvidence,
    DecisionUnitListResponse,
    DecisionUnitSummary,
    DecisionUnitFeedbackCreate,
    DecisionUnitFeedback,
)


router = APIRouter()


def _parse_uuid(raw: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        ) from exc


_ALLOWED_FEEDBACK_LABELS = {"correct", "incorrect", "mismatch", "valuable", "worthless"}


def _validate_feedback_label(label: str) -> str:
    cleaned = (label or "").strip().lower()
    if cleaned not in _ALLOWED_FEEDBACK_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid feedback label",
        )
    return cleaned


@router.get(
    "/decision-units",
    response_model=DecisionUnitListResponse,
    summary="获取 DecisionUnits 列表（平台级主合同）",
    tags=["decision-units"],
)
async def list_decision_units(
    task_id: UUID | None = Query(default=None, description="可选：只看某个 task 的决策单元"),
    concept_id: int | None = Query(default=None, ge=1, description="可选：按概念过滤"),
    signal_type: str | None = Query(default=None, max_length=20, description="可选：按信号类型过滤"),
    limit: int = Query(default=50, ge=1, le=200, description="分页大小（最多 200）"),
    offset: int = Query(default=0, ge=0, description="分页偏移"),
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> DecisionUnitListResponse:
    user_uuid = _parse_uuid(payload.sub)

    where_sql = "t.user_id = :user_id"
    params: dict[str, object] = {"user_id": user_uuid, "limit": limit, "offset": offset}

    if task_id is not None:
        where_sql += " AND du.task_id = :task_id"
        params["task_id"] = task_id
    if concept_id is not None:
        where_sql += " AND du.concept_id = :concept_id"
        params["concept_id"] = concept_id
    if signal_type is not None and signal_type.strip():
        where_sql += " AND du.signal_type = :signal_type"
        params["signal_type"] = signal_type.strip()

    total = int(
        (
            await db.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM decision_units_v du
                    JOIN tasks t ON t.id = du.task_id
                    WHERE {where_sql}
                    """
                ),
                params,
            )
        ).scalar_one()
        or 0
    )

    rows = (
        await db.execute(
            text(
                f"""
                SELECT
                    du.id,
                    du.task_id,
                    du.title,
                    du.summary,
                    du.confidence,
                    du.time_window_days,
                    du.subreddits,
                    du.concept_id,
                    du.signal_type,
                    du.du_schema_version,
                    du.du_payload,
                    du.created_at,
                    du.updated_at
                FROM decision_units_v du
                JOIN tasks t ON t.id = du.task_id
                WHERE {where_sql}
                ORDER BY du.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
    ).mappings().all()

    items = [
        DecisionUnitSummary(
            id=row["id"],
            task_id=row["task_id"],
            title=row["title"],
            summary=row["summary"],
            confidence=float(row["confidence"]),
            time_window_days=int(row["time_window_days"]),
            subreddits=list(row["subreddits"] or []),
            concept_id=row.get("concept_id"),
            signal_type=row.get("signal_type"),
            du_schema_version=row.get("du_schema_version"),
            du_payload=dict(row.get("du_payload") or {}),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]

    return DecisionUnitListResponse(total=total, items=items)


@router.get(
    "/decision-units/{decision_unit_id}",
    response_model=DecisionUnitDetail,
    summary="获取 DecisionUnit 详情（含证据链）",
    tags=["decision-units"],
)
async def get_decision_unit_detail(
    decision_unit_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> DecisionUnitDetail:
    user_uuid = _parse_uuid(payload.sub)

    row = (
        await db.execute(
            text(
                """
                SELECT
                    du.id,
                    du.task_id,
                    du.title,
                    du.summary,
                    du.confidence,
                    du.time_window_days,
                    du.subreddits,
                    du.concept_id,
                    du.signal_type,
                    du.du_schema_version,
                    du.du_payload,
                    du.created_at,
                    du.updated_at
                FROM decision_units_v du
                JOIN tasks t ON t.id = du.task_id
                WHERE du.id = :id AND t.user_id = :user_id
                LIMIT 1
                """
            ),
            {"id": decision_unit_id, "user_id": user_uuid},
        )
    ).mappings().first()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DecisionUnit not found")

    evidence_rows = (
        await db.execute(
            text(
                """
                SELECT
                    id,
                    post_url,
                    excerpt,
                    timestamp,
                    subreddit,
                    score,
                    content_type,
                    content_id
                FROM evidences
                WHERE insight_card_id = :card_id
                ORDER BY score DESC NULLS LAST, created_at DESC
                """
            ),
            {"card_id": decision_unit_id},
        )
    ).mappings().all()

    evidence = [
        DecisionUnitEvidence(
            id=e["id"],
            post_url=e["post_url"],
            excerpt=e["excerpt"],
            timestamp=e["timestamp"],
            subreddit=e["subreddit"],
            score=float(e["score"]) if e["score"] is not None else None,
            content_type=e.get("content_type"),
            content_id=e.get("content_id"),
        )
        for e in evidence_rows
    ]

    return DecisionUnitDetail(
        id=row["id"],
        task_id=row["task_id"],
        title=row["title"],
        summary=row["summary"],
        confidence=float(row["confidence"]),
        time_window_days=int(row["time_window_days"]),
        subreddits=list(row["subreddits"] or []),
        concept_id=row.get("concept_id"),
        signal_type=row.get("signal_type"),
        du_schema_version=row.get("du_schema_version"),
        du_payload=dict(row.get("du_payload") or {}),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        evidence=evidence,
    )


@router.post(
    "/decision-units/{decision_unit_id}/feedback",
    response_model=DecisionUnitFeedback,
    status_code=status.HTTP_201_CREATED,
    summary="提交 DecisionUnit 反馈（append-only）",
    tags=["decision-units"],
)
async def submit_decision_unit_feedback(
    decision_unit_id: UUID,
    body: DecisionUnitFeedbackCreate,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> DecisionUnitFeedback:
    """Append-only feedback bound to a DecisionUnit + (optional) evidence."""
    from app.models.decision_unit_feedback_event import DecisionUnitFeedbackEvent

    user_uuid = _parse_uuid(payload.sub)
    label = _validate_feedback_label(body.label)

    du_row = (
        await db.execute(
            text(
                """
                SELECT
                    du.id,
                    du.task_id,
                    t.topic_profile_id
                FROM decision_units_v du
                JOIN tasks t ON t.id = du.task_id
                WHERE du.id = :id AND t.user_id = :user_id
                LIMIT 1
                """
            ),
            {"id": decision_unit_id, "user_id": user_uuid},
        )
    ).mappings().first()

    if du_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DecisionUnit not found")

    task_id = uuid.UUID(str(du_row["task_id"]))
    topic_profile_id = du_row.get("topic_profile_id")

    evidence_id = body.evidence_id
    if evidence_id is not None:
        ok = (
            await db.execute(
                text(
                    """
                    SELECT 1
                    FROM evidences
                    WHERE id = :evidence_id AND insight_card_id = :du_id
                    LIMIT 1
                    """
                ),
                {"evidence_id": evidence_id, "du_id": decision_unit_id},
            )
        ).scalar()
        if ok is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Evidence does not belong to this DecisionUnit",
            )
    else:
        evidence_id = (
            await db.execute(
                text(
                    """
                    SELECT id
                    FROM evidences
                    WHERE insight_card_id = :du_id
                    ORDER BY score DESC NULLS LAST, created_at DESC
                    LIMIT 1
                    """
                ),
                {"du_id": decision_unit_id},
            )
        ).scalar_one_or_none()
        if evidence_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No evidence available for this DecisionUnit",
            )

    # Soft dedupe: avoid accidental double clicks in a short time window.
    try:
        window_s = int(os.getenv("DECISION_UNIT_FEEDBACK_DEDUPE_WINDOW_SECONDS", "120"))
    except ValueError:
        window_s = 120
    window_s = max(0, min(window_s, 3600))
    if window_s > 0:
        existing = (
            await db.execute(
                text(
                    """
                    SELECT id, created_at, note, meta, evidence_id
                    FROM decision_unit_feedback_events
                    WHERE decision_unit_id = :du_id
                      AND user_id = :user_id
                      AND evidence_id = :evidence_id
                      AND label = :label
                      AND created_at >= (now() - (:window_s * INTERVAL '1 second'))
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {
                    "du_id": decision_unit_id,
                    "user_id": user_uuid,
                    "evidence_id": evidence_id,
                    "label": label,
                    "window_s": window_s,
                },
            )
        ).mappings().first()
        if existing is not None:
            # Return existing entry (idempotent-ish). Status code 200 is acceptable for dedupe.
            return DecisionUnitFeedback(
                id=existing["id"],
                decision_unit_id=decision_unit_id,
                task_id=task_id,
                topic_profile_id=topic_profile_id,
                user_id=user_uuid,
                evidence_id=existing.get("evidence_id") or evidence_id,
                label=label,
                note=str(existing.get("note") or ""),
                meta=dict(existing.get("meta") or {}),
                created_at=existing["created_at"],
            )

    event = DecisionUnitFeedbackEvent(
        decision_unit_id=decision_unit_id,
        task_id=task_id,
        topic_profile_id=str(topic_profile_id) if topic_profile_id else None,
        user_id=user_uuid,
        evidence_id=evidence_id,
        label=label,
        note=str(body.note or ""),
        meta=dict(body.meta or {}),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    return DecisionUnitFeedback(
        id=event.id,
        decision_unit_id=decision_unit_id,
        task_id=task_id,
        topic_profile_id=event.topic_profile_id,
        user_id=user_uuid,
        evidence_id=event.evidence_id,
        label=event.label,
        note=event.note,
        meta=dict(event.meta or {}),
        created_at=event.created_at,
    )


__all__ = ["router"]
