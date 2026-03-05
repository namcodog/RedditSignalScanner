from __future__ import annotations

"""Celery 任务：每日生成社区 Tier 调级建议，并可选自动应用高置信度建议。"""

from datetime import datetime, timezone, timedelta
import os
import uuid
from typing import Any, Dict, List

from celery.utils.log import get_task_logger  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.models.tier_audit_log import TierAuditLog
from app.models.tier_suggestion import TierSuggestion
from app.models.user import User
from app.services.ops.tier_suggestion_decision_units import (
    emit_tier_suggestions_as_decision_units,
)
from app.services.analysis.tier_intelligence import TierIntelligenceService, TierThresholds

logger = get_task_logger(__name__)


async def _apply_high_confidence_suggestions(
    session: AsyncSession,
    suggestions: List[TierSuggestion],
) -> None:
    """自动应用高置信度建议（confidence >= 0.9 且社区开启 auto_tier_enabled）。"""

    now = datetime.now(timezone.utc)
    high_confidence = [s for s in suggestions if s.confidence >= 0.9]

    applied = 0
    for sugg in high_confidence:
        comm = await session.scalar(
            select(CommunityPool).where(
                CommunityPool.name == sugg.community_name,
                CommunityPool.auto_tier_enabled.is_(True),
                CommunityPool.is_active.is_(True),
            )
        )
        if comm is None:
            continue

        old_tier = comm.tier
        comm.tier = sugg.suggested_tier

        sugg.status = "auto_applied"
        sugg.reviewed_by = "system"
        sugg.reviewed_at = now
        sugg.applied_at = now

        log = TierAuditLog(
            community_name=comm.name,
            action="tier_change",
            field_changed="tier",
            from_value=old_tier,
            to_value=sugg.suggested_tier,
            changed_by="system",
            change_source="auto",
            reason=f"自动应用高置信度建议 (ID: {sugg.id}, 置信度: {sugg.confidence})",
            snapshot_before={"tier": old_tier},
            snapshot_after={"tier": comm.tier},
            suggestion_id=sugg.id,
        )
        session.add(log)
        applied += 1

    if applied:
        logger.info("Auto-applied %s high confidence tier suggestions", applied)


async def _generate_daily_tier_suggestions_impl() -> Dict[str, Any]:
    """每日生成调级建议的异步实现。"""

    async with SessionFactory() as session:
        service = TierIntelligenceService(session)
        thresholds = TierThresholds()

        suggestions = await service.generate_tier_suggestions(thresholds=thresholds)

        records: List[TierSuggestion] = []
        now = datetime.now(timezone.utc)
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
            # 确保生成了主键 ID，便于后续审计日志引用
            await session.flush()

        # 可选：自动应用高置信度建议
        auto_enabled = os.getenv("ENABLE_AUTO_TIER_APPLICATION", "true").strip().lower()
        if auto_enabled in {"1", "true", "yes"} and records:
            await _apply_high_confidence_suggestions(session, records)

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
            "generated_at": now.isoformat(),
            "auto_apply_enabled": auto_enabled in {"1", "true", "yes"},
        }
        logger.info("Daily tier suggestions generated: %s", summary)
        return summary


@celery_app.task(name="tasks.tier.generate_daily_suggestions")  # type: ignore[misc]
def generate_daily_tier_suggestions() -> Dict[str, Any]:
    """Celery 入口：每日生成社区 Tier 调级建议。"""

    import asyncio

    return asyncio.run(_generate_daily_tier_suggestions_impl())


def _parse_uuid_env(raw: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(raw)
    except Exception:
        return None


async def _resolve_ops_owner_user_id(session: AsyncSession) -> uuid.UUID | None:
    """Resolve which user owns ops DecisionUnits (best-effort, no exceptions)."""
    raw_user_id = os.getenv("OPS_DECISION_UNIT_USER_ID", "").strip()
    if raw_user_id:
        parsed = _parse_uuid_env(raw_user_id)
        if parsed is not None:
            return parsed

    raw_email = os.getenv("OPS_DECISION_UNIT_USER_EMAIL", "").strip().lower()
    if not raw_email:
        raw_admins = os.getenv("ADMIN_EMAILS", "").strip()
        if raw_admins:
            first = [x.strip().lower() for x in raw_admins.split(",") if x.strip()]
            raw_email = first[0] if first else ""

    if not raw_email:
        return None

    user_id = await session.scalar(select(User.id).where(User.email == raw_email))
    if user_id is None:
        return None
    return uuid.UUID(str(user_id))


async def _emit_daily_tier_suggestion_decision_units_impl() -> Dict[str, Any]:
    """把当天可用的 tier_suggestions 转成 ops DecisionUnits（第一条运营生产线）。"""
    now = datetime.now(timezone.utc)

    try:
        limit = int(os.getenv("OPS_TIER_SUGGESTIONS_EMIT_LIMIT", "100"))
    except ValueError:
        limit = 100
    limit = max(1, min(limit, 500))

    try:
        lookback_days = int(os.getenv("OPS_TIER_SUGGESTIONS_EVIDENCE_LOOKBACK_DAYS", "30"))
    except ValueError:
        lookback_days = 30
    lookback_days = max(1, min(lookback_days, 3650))

    try:
        max_evidence_posts = int(os.getenv("OPS_TIER_SUGGESTIONS_MAX_EVIDENCE_POSTS", "3"))
    except ValueError:
        max_evidence_posts = 3
    max_evidence_posts = max(1, min(max_evidence_posts, 10))

    try:
        min_confidence_raw = os.getenv("OPS_TIER_SUGGESTIONS_MIN_CONFIDENCE", "").strip()
        min_confidence = float(min_confidence_raw) if min_confidence_raw else None
    except ValueError:
        min_confidence = None

    async with SessionFactory() as session:
        owner_id = await _resolve_ops_owner_user_id(session)
        if owner_id is None:
            logger.info("Skip ops DecisionUnit emission: missing OPS_DECISION_UNIT_USER_* / ADMIN_EMAILS")
            return {"status": "skipped", "reason": "missing_ops_owner"}

        stmt = select(TierSuggestion).where(
            TierSuggestion.status == "pending",
            TierSuggestion.expires_at > now,
        )
        if min_confidence is not None:
            stmt = stmt.where(TierSuggestion.confidence >= float(min_confidence))

        stmt = stmt.order_by(
            TierSuggestion.priority_score.desc(),
            TierSuggestion.generated_at.desc(),
        ).limit(limit)

        suggestions = (await session.execute(stmt)).scalars().all()
        if not suggestions:
            return {"status": "ok", "owner_user_id": str(owner_id), "suggestions": 0, "created_units": 0}

        result = await emit_tier_suggestions_as_decision_units(
            session,
            user_id=owner_id,
            suggestions=suggestions,
            emitted_at=now,
            lookback_days=lookback_days,
            max_evidence_posts=max_evidence_posts,
        )

        # Lightweight run ledger (best-effort; no exception propagation).
        try:
            from sqlalchemy import text as sqltext

            await session.execute(
                sqltext(
                    """
                    INSERT INTO data_audit_events (event_type, target_type, target_id, reason, source_component, new_value)
                    VALUES (:event_type, :target_type, :target_id, :reason, :source_component, :new_value)
                    """
                ),
                {
                    "event_type": "ops_emit",
                    "target_type": "decision_units",
                    "target_id": str(result.task_id),
                    "reason": "tier_suggestions",
                    "source_component": "tasks.tier.emit_daily_suggestion_decision_units",
                    "new_value": {
                        "owner_user_id": str(owner_id),
                        "suggestions": len(suggestions),
                        "created_units": result.created_units,
                        "skipped_existing_units": result.skipped_existing_units,
                        "created_evidences": result.created_evidences,
                        "lookback_days": lookback_days,
                        "max_evidence_posts": max_evidence_posts,
                        "min_confidence": min_confidence,
                        "generated_at": now.isoformat(),
                    },
                },
            )
            await session.commit()
        except Exception:
            # Ignore ledger failures (do not fail the scheduled job).
            pass

        return {
            "status": "ok",
            "owner_user_id": str(owner_id),
            "task_id": str(result.task_id),
            "suggestions": len(suggestions),
            "created_units": result.created_units,
            "skipped_existing_units": result.skipped_existing_units,
            "created_evidences": result.created_evidences,
        }


@celery_app.task(name="tasks.tier.emit_daily_suggestion_decision_units")  # type: ignore[misc]
def emit_daily_tier_suggestion_decision_units() -> Dict[str, Any]:
    """Celery 入口：把待审核的调级建议翻译成 ops DecisionUnits（不改变建议状态）。"""
    import asyncio

    return asyncio.run(_emit_daily_tier_suggestion_decision_units_impl())


__all__ = [
    "generate_daily_tier_suggestions",
    "_generate_daily_tier_suggestions_impl",
    "emit_daily_tier_suggestion_decision_units",
    "_emit_daily_tier_suggestion_decision_units_impl",
]
