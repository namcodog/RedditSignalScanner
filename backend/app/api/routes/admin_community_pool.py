from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, nullslast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.admin import _response
from app.core.auth import require_admin
from app.core.security import TokenPayload
from app.db.session import get_session
from app.models.community_pool import CommunityPool
from app.models.discovered_community import DiscoveredCommunity
from app.models.evidence_post import EvidencePost
from app.models.tier_audit_log import TierAuditLog
from app.models.tier_suggestion import TierSuggestion
from app.services.tier_intelligence import TierIntelligenceService, TierThresholds
from app.services.community_category_map_service import replace_community_category_map
from app.services.ops.tier_suggestion_decision_units import emit_tier_suggestions_as_decision_units

router = APIRouter(prefix="/admin/communities", tags=["admin"])  # mounted under /api
logger = logging.getLogger(__name__)


def safe_int(value: Any) -> int:
    """Convert values to int while preserving logging hook for tests."""
    return int(value)


def _safe_actor(actor: str | None) -> str:
    # DB 兼容最旧的 varchar(50) 定义，裁切长度避免插入超长
    return (actor or "admin")[:48]


def _safe_value(value: Any) -> str:
    return str(value)[:50]


class ApproveRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    tier: str = Field("medium", min_length=3, max_length=20)
    categories: Dict[str, Any] | None = None
    admin_notes: Optional[str] = None


class RejectRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    admin_notes: Optional[str] = None


class BatchUpdateFields(BaseModel):
    tier: str | None = None
    priority: str | None = None
    is_active: bool | None = None
    downrank_factor: float | None = None
    auto_tier_enabled: bool | None = None


class BatchUpdateRequest(BaseModel):
    communities: list[str] = Field(..., min_items=1)
    updates: BatchUpdateFields
    reason: str | None = Field(
        None,
        max_length=2000,
        description="本次批量修改的原因，写入审计日志",
    )


class ThresholdConfig(BaseModel):
    min_posts_per_day: float | None = None
    max_posts_per_day: float | None = None
    min_pain_density: float | None = None
    max_pain_density: float | None = None
    min_semantic_score: float | None = None
    min_labeling_coverage: float | None = None
    min_growth_rate: float | None = None
    max_growth_rate: float | None = None


class RemoveThresholdConfig(BaseModel):
    max_posts_per_day: float | None = None
    max_spam_ratio: float | None = None
    min_labeling_coverage: float | None = None


class TierThresholdsPayload(BaseModel):
    promote_to_t1: ThresholdConfig | None = None
    promote_to_t2: ThresholdConfig | None = None
    demote_to_t3: ThresholdConfig | None = None
    remove_from_pool: RemoveThresholdConfig | None = None


class TierSuggestionsRequest(BaseModel):
    thresholds: TierThresholdsPayload | None = None
    target_communities: list[str] | None = None


class ApplySuggestionsRequest(BaseModel):
    suggestion_ids: list[int] = Field(..., min_items=1)


class EmitDecisionUnitsRequest(BaseModel):
    suggestion_ids: list[int] | None = None
    limit: int = Field(100, ge=1, le=500, description="最多处理多少条建议（防止一次性刷爆）")
    min_confidence: float | None = Field(None, ge=0.0, le=1.0)
    lookback_days: int = Field(30, ge=1, le=3650)
    max_evidence_posts: int = Field(3, ge=1, le=10)


class RollbackRequest(BaseModel):
    audit_log_id: int
    reason: str = Field(..., min_length=1, max_length=2000)


@router.get("/tier-suggestions", summary="查看社区调级建议列表")
async def list_tier_suggestions(
    community_name: str | None = Query(
        None,
        description="按社区名过滤（r/xxx）",
    ),
    status: str | None = Query(
        None,
        description="按建议状态过滤：pending/applied/auto_applied/rejected 等",
    ),
    min_confidence: float | None = Query(
        None,
        ge=0.0,
        le=1.0,
        description="只返回置信度大于等于该值的建议",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    stmt = select(TierSuggestion)
    if community_name:
        stmt = stmt.where(TierSuggestion.community_name == community_name)
    if status:
        stmt = stmt.where(TierSuggestion.status == status)
    if min_confidence is not None:
        stmt = stmt.where(TierSuggestion.confidence >= min_confidence)

    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))

    stmt = (
        stmt.order_by(
            TierSuggestion.priority_score.desc(),
            TierSuggestion.generated_at.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    records = result.scalars().all()

    items: list[dict[str, Any]] = []
    for rec in records:
        items.append(
            {
                "id": rec.id,
                "community_name": rec.community_name,
                "current_tier": rec.current_tier,
                "suggested_tier": rec.suggested_tier,
                "confidence": rec.confidence,
                "status": rec.status,
                "priority_score": rec.priority_score,
                "reasons": rec.reasons,
                "generated_at": rec.generated_at,
                "reviewed_by": rec.reviewed_by,
                "reviewed_at": rec.reviewed_at,
                "applied_at": rec.applied_at,
                "expires_at": rec.expires_at,
            }
        )

    return _response(
        {
            "items": items,
            "total": int(total or 0),
            "page": page,
            "page_size": page_size,
        }
    )


@router.post(
    "/tier-suggestions/emit-decision-units",
    summary="把调级建议翻译成 ops DecisionUnits（带证据链）",
)
async def emit_tier_suggestion_decision_units(
    req: EmitDecisionUnitsRequest,
    session: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    """Admin 手动触发：把 tier_suggestions 产出成 DecisionUnits。

    大白话：这是“生产线通水”的手动阀门，方便你调试/复盘/上线初期补跑。
    """
    now = datetime.now(timezone.utc)
    admin_user_id = uuid.UUID(payload.sub)

    stmt = select(TierSuggestion).where(TierSuggestion.expires_at > now)
    if req.suggestion_ids:
        stmt = stmt.where(TierSuggestion.id.in_(list(req.suggestion_ids)))
    else:
        stmt = stmt.where(TierSuggestion.status == "pending")
    if req.min_confidence is not None:
        stmt = stmt.where(TierSuggestion.confidence >= float(req.min_confidence))

    stmt = stmt.order_by(
        TierSuggestion.priority_score.desc(),
        TierSuggestion.generated_at.desc(),
    ).limit(int(req.limit))

    suggestions = (await session.execute(stmt)).scalars().all()

    result = await emit_tier_suggestions_as_decision_units(
        session,
        user_id=admin_user_id,
        suggestions=suggestions,
        emitted_at=now,
        lookback_days=int(req.lookback_days),
        max_evidence_posts=int(req.max_evidence_posts),
    )

    return _response(
        {
            "task_id": str(result.task_id),
            "suggestions": len(suggestions),
            "created_units": result.created_units,
            "skipped_existing_units": result.skipped_existing_units,
            "created_evidences": result.created_evidences,
        }
    )


@router.get("/pool", summary="查看社区池（增强版）")
async def list_community_pool(
    tier: str | None = Query(
        None,
        description="按 tier 过滤（如 T1/T2/T3）",
    ),
    priority: str | None = Query(
        None,
        description="按优先级过滤（high/medium/low）",
    ),
    is_active: bool | None = Query(
        None,
        description="是否仅查看启用/禁用社区",
    ),
    health_status: str | None = Query(
        None,
        description="按健康状态过滤（healthy/warning/critical/unknown）",
    ),
    sort_by: str = Query(
        "quality_score",
        regex="^(quality_score|daily_posts|avg_comment_length|name)$",
        description="排序字段",
    ),
    order: str = Query(
        "desc",
        regex="^(asc|desc)$",
        description="排序方向",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    # 在直接函数调用（非 FastAPI 路由上下文）时，Query(...) 可能未被解析，需兜底转 None/默认值
    from fastapi.params import Query as QueryParam

    if isinstance(tier, QueryParam):
        tier = None
    if isinstance(priority, QueryParam):
        priority = None
    if isinstance(is_active, QueryParam):
        is_active = None
    if isinstance(health_status, QueryParam):
        health_status = None
    if isinstance(sort_by, QueryParam):
        sort_by = "quality_score"
    if isinstance(order, QueryParam):
        order = "desc"
    if isinstance(page, QueryParam):
        page = 1
    if isinstance(page_size, QueryParam):
        page_size = 200

    stmt = select(CommunityPool).where(CommunityPool.deleted_at.is_(None))

    if tier:
        stmt = stmt.where(CommunityPool.tier == tier)
    if priority:
        stmt = stmt.where(CommunityPool.priority == priority)
    if is_active is not None:
        stmt = stmt.where(CommunityPool.is_active.is_(is_active))
    if health_status:
        stmt = stmt.where(CommunityPool.health_status == health_status)

    # 统计总数
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))

    # 排序与分页
    sort_attr = getattr(CommunityPool, sort_by)
    if order == "desc":
        stmt = stmt.order_by(sort_attr.desc())
    else:
        stmt = stmt.order_by(sort_attr.asc())

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    items = result.scalars().all()

    tier_service = TierIntelligenceService(session)
    enriched_items: list[dict[str, Any]] = []

    for c in items:
        # 计算近 7 天轻量指标，用于前端列表展示
        metrics = await tier_service.calculate_community_metrics(
            c.name,
            lookback_days=7,
        )
        suggested_tier = await tier_service.get_latest_suggested_tier(c.name)

        enriched_items.append(
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
                "health_status": c.health_status,
                "auto_tier_enabled": c.auto_tier_enabled,
                "recent_metrics": {
                    "posts_7d": int(metrics.posts_per_day * 7),
                    "comments_7d": int(metrics.comments_per_day * 7),
                    "pain_density_30d": metrics.pain_density,
                    "brand_mentions_30d": metrics.brand_mentions,
                },
                "tier_suggestion": suggested_tier,
            }
        )

    data = {
        "items": enriched_items,
        "total": int(total or 0),
        "page": page,
        "page_size": page_size,
    }
    return _response(data)


@router.get("/discovered", summary="查看待审核社区")
async def list_discovered(
    evidence_limit: int = Query(3, ge=1, le=10, description="每个社区返回的证据帖数量上限"),
    session: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    from fastapi.params import Query as QueryParam

    if isinstance(evidence_limit, QueryParam):
        evidence_limit = 3

    stmt = (
        select(DiscoveredCommunity)
        .where(
            DiscoveredCommunity.status == "pending",
            DiscoveredCommunity.deleted_at.is_(None),
        )
        .order_by(DiscoveredCommunity.last_discovered_at.desc())
    )
    result = await session.execute(stmt)
    items = result.scalars().all()

    evidence_posts_by_sub: dict[str, list[dict[str, Any]]] = {}
    if items:
        names = [p.name for p in items]
        ev_stmt = (
            select(EvidencePost)
            .where(EvidencePost.subreddit.in_(names))
            .order_by(
                EvidencePost.subreddit.asc(),
                EvidencePost.evidence_score.desc(),
                nullslast(EvidencePost.post_created_at.desc()),
                EvidencePost.id.desc(),
            )
        )
        ev_result = await session.execute(ev_stmt)
        for post in ev_result.scalars().all():
            bucket = evidence_posts_by_sub.setdefault(post.subreddit, [])
            if len(bucket) >= evidence_limit:
                continue
            bucket.append(
                {
                    "source_post_id": post.source_post_id,
                    "title": post.title,
                    "summary": post.summary,
                    "score": post.score,
                    "num_comments": post.num_comments,
                    "post_created_at": post.post_created_at,
                    "evidence_score": post.evidence_score,
                    "probe_source": post.probe_source,
                    "source_query": post.source_query,
                }
            )

    data = {
        "items": [
            {
                "name": p.name,
                "discovered_from_keywords": p.discovered_from_keywords,
                "discovered_count": p.discovered_count,
                "first_discovered_at": p.first_discovered_at,
                "last_discovered_at": p.last_discovered_at,
                "status": p.status,
                "evidence_posts": evidence_posts_by_sub.get(p.name, []),
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
        select(DiscoveredCommunity).where(DiscoveredCommunity.name == body.name)
    )
    if pending is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Discovered community not found"
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
        categories = body.categories
        pool = CommunityPool(
            name=body.name,
            tier=body.tier,
            categories=[],
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
        await session.flush()
        if categories is not None:
            await replace_community_category_map(
                session,
                community_id=pool.id,
                categories=categories,
            )
    else:
        pool.is_active = True
        pool.deleted_at = None
        pool.deleted_by = None
        pool.updated_by = reviewer_id
        # 如果社区已存在，允许管理员在审批时更新 tier
        pool.tier = body.tier
        try:
            pool.discovered_count = safe_int(pool.discovered_count) + safe_int(
                pending.discovered_count
            )
        except Exception as exc:
            logger.warning(
                "无法累加 discovered_count，使用待审核值覆盖: %s", exc,
            )
            pool.discovered_count = safe_int(pending.discovered_count)
        if body.categories is not None:
            await replace_community_category_map(
                session,
                community_id=pool.id,
                categories=body.categories,
            )

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
        select(DiscoveredCommunity).where(DiscoveredCommunity.name == body.name)
    )
    if pending is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Discovered community not found"
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


@router.patch("/batch", summary="批量更新社区配置")
async def batch_update_community_pool(
    body: BatchUpdateRequest,
    session: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    stmt = select(CommunityPool).where(CommunityPool.name.in_(body.communities))
    result = await session.execute(stmt)
    communities = result.scalars().all()

    if not communities:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到目标社区",
        )

    updated_count = 0
    logs: list[TierAuditLog] = []

    actor_email = _safe_actor((payload.email or "").strip())

    for comm in communities:
        snapshot_before = {
            "tier": comm.tier,
            "priority": comm.priority,
            "is_active": comm.is_active,
            "downrank_factor": float(comm.downrank_factor) if comm.downrank_factor is not None else None,
            "auto_tier_enabled": comm.auto_tier_enabled,
        }

        if body.updates.tier is not None:
            comm.tier = body.updates.tier
        if body.updates.priority is not None:
            comm.priority = body.updates.priority
        if body.updates.is_active is not None:
            comm.is_active = body.updates.is_active
        if body.updates.downrank_factor is not None:
            comm.downrank_factor = body.updates.downrank_factor
        if body.updates.auto_tier_enabled is not None:
            comm.auto_tier_enabled = body.updates.auto_tier_enabled

        snapshot_after = {
            "tier": comm.tier,
            "priority": comm.priority,
            "is_active": comm.is_active,
            "downrank_factor": float(comm.downrank_factor) if comm.downrank_factor is not None else None,
            "auto_tier_enabled": comm.auto_tier_enabled,
        }

        logs.append(
            TierAuditLog(
                community_name=comm.name,
                action="batch_update",
                field_changed="multiple",
                from_value=_safe_value(snapshot_before),
                to_value=_safe_value(snapshot_after),
                changed_by=actor_email,
                change_source="manual",
                reason=body.reason,
                snapshot_before=snapshot_before,
                snapshot_after=snapshot_after,
            )
        )
        updated_count += 1

    session.add_all(logs)
    await session.commit()

    return _response(
        {
            "updated_count": updated_count,
            "communities": [c.name for c in communities],
        }
    )


def _build_thresholds_from_payload(payload: TierThresholdsPayload | None) -> TierThresholds:
    if payload is None:
        return TierThresholds()

    def _to_kwargs(model: BaseModel | None) -> dict[str, Any]:
        if model is None:
            return {}
        return model.model_dump(exclude_unset=True, exclude_none=True)

    return TierThresholds(
        promote_to_t1=TierThresholds.PromoteToT1(**_to_kwargs(payload.promote_to_t1)),
        promote_to_t2=TierThresholds.PromoteToT2(**_to_kwargs(payload.promote_to_t2)),
        demote_to_t3=TierThresholds.DemoteToT3(**_to_kwargs(payload.demote_to_t3)),
        remove_from_pool=TierThresholds.RemoveFromPool(**_to_kwargs(payload.remove_from_pool)),
    )


@router.post("/suggest-tier-adjustments", summary="生成社区 Tier 调级建议")
async def generate_tier_suggestions(
    body: TierSuggestionsRequest,
    session: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    service = TierIntelligenceService(session)
    thresholds = _build_thresholds_from_payload(body.thresholds)

    suggestions = await service.generate_tier_suggestions(
        thresholds=thresholds,
        target_communities=body.target_communities,
    )

    # 持久化到 tier_suggestions 表
    records: list[TierSuggestion] = []
    now = datetime.now(timezone.utc)
    from datetime import timedelta

    expires_at = now + timedelta(days=7)

    for item in suggestions:
        record = TierSuggestion(
            community_name=item["community"],
            current_tier=item["current_tier"],
            suggested_tier=item["suggested_tier"],
            confidence=item["confidence"],
            reasons=item["reasons"],
            metrics=item["metrics"],
            priority_score=item["priority_score"],
            expires_at=expires_at,
        )
        records.append(record)

    if records:
        session.add_all(records)
        await session.commit()

    summary = {
        "total_suggestions": len(suggestions),
        "promote_to_t1": len(
            [s for s in suggestions if s["suggested_tier"] == "T1"]
        ),
        "promote_to_t2": len(
            [s for s in suggestions if s["suggested_tier"] == "T2"]
        ),
        "demote_to_t3": len(
            [s for s in suggestions if s["suggested_tier"] == "T3"]
        ),
        "remove_from_pool": len(
            [s for s in suggestions if s["suggested_tier"] == "REMOVE"]
        ),
    }

    return _response({"suggestions": suggestions, "summary": summary})


@router.post("/apply-suggestions", summary="应用调级建议")
async def apply_tier_suggestions(
    body: ApplySuggestionsRequest,
    session: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    stmt = select(TierSuggestion).where(
        TierSuggestion.id.in_(body.suggestion_ids),
        TierSuggestion.status == "pending",
    )
    result = await session.execute(stmt)
    suggestions = result.scalars().all()

    if not suggestions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到待应用的建议",
        )

    actor_email = _safe_actor((payload.email or "").strip())
    now = datetime.now(timezone.utc)
    applied_count = 0

    for sugg in suggestions:
        comm = await session.scalar(
            select(CommunityPool).where(CommunityPool.name == sugg.community_name)
        )
        if comm is None:
            continue

        old_tier = comm.tier
        comm.tier = sugg.suggested_tier

        sugg.status = "applied"
        sugg.reviewed_by = actor_email
        sugg.reviewed_at = now
        sugg.applied_at = now

        log = TierAuditLog(
            community_name=comm.name,
            action="tier_change",
            field_changed="tier",
            from_value=_safe_value(old_tier),
            to_value=_safe_value(sugg.suggested_tier),
            changed_by=actor_email,
            change_source="suggestion",
            reason=f"应用调级建议 (ID: {sugg.id})",
            snapshot_before={"tier": old_tier},
            snapshot_after={"tier": comm.tier},
            suggestion_id=sugg.id,
        )
        session.add(log)
        applied_count += 1

    await session.commit()

    return _response(
        {
            "applied_count": applied_count,
            "applied_suggestions": [s.id for s in suggestions],
        }
    )


@router.post("/rollback", summary="回滚社区 Tier 变更")
async def rollback_tier_change(
    body: RollbackRequest,
    session: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    log = await session.scalar(
        select(TierAuditLog).where(
            TierAuditLog.id == body.audit_log_id,
            TierAuditLog.is_rolled_back.is_(False),
        )
    )
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到可回滚的操作记录",
        )

    comm = await session.scalar(
        select(CommunityPool).where(CommunityPool.name == log.community_name)
    )
    if comm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="社区不存在",
        )

    snapshot_before = log.snapshot_before
    for field, value in snapshot_before.items():
        setattr(comm, field, value)

    actor_email = _safe_actor((payload.email or "").strip())
    now = datetime.now(timezone.utc)

    log.is_rolled_back = True
    log.rolled_back_at = now
    log.rolled_back_by = actor_email

    rollback_log = TierAuditLog(
        community_name=comm.name,
        action="rollback",
        field_changed=log.field_changed,
        from_value=_safe_value(log.to_value),
        to_value=_safe_value(log.from_value),
        changed_by=actor_email,
        change_source="manual",
        reason=f"回滚操作(原日志ID: {log.id}): {body.reason}",
        snapshot_before=log.snapshot_after,
        snapshot_after=log.snapshot_before,
        suggestion_id=log.suggestion_id,
    )
    session.add(rollback_log)

    await session.commit()

    return _response(
        {
            "success": True,
            "community": comm.name,
            "rolled_back_to": snapshot_before,
        }
    )


@router.get("/{name:path}/tier-audit-logs", summary="查看社区 Tier 调整历史")
async def list_tier_audit_logs(
    name: str = Path(..., min_length=2, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, Any]:
    stmt = select(TierAuditLog).where(TierAuditLog.community_name == name)
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))

    stmt = (
        stmt.order_by(TierAuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    records = result.scalars().all()

    items: list[dict[str, Any]] = []
    for rec in records:
        items.append(
            {
                "id": rec.id,
                "community_name": rec.community_name,
                "action": rec.action,
                "field_changed": rec.field_changed,
                "from_value": rec.from_value,
                "to_value": rec.to_value,
                "changed_by": rec.changed_by,
                "change_source": rec.change_source,
                "reason": rec.reason,
                "snapshot_before": rec.snapshot_before,
                "snapshot_after": rec.snapshot_after,
                "suggestion_id": rec.suggestion_id,
                "is_rolled_back": rec.is_rolled_back,
                "rolled_back_at": rec.rolled_back_at,
                "rolled_back_by": rec.rolled_back_by,
                "created_at": rec.created_at,
            }
        )

    return _response(
        {
            "items": items,
            "total": int(total or 0),
            "page": page,
            "page_size": page_size,
        }
    )


__all__ = ["router"]
