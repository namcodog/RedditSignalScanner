from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import uuid
from typing import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insight import Evidence, InsightCard
from app.models.posts_storage import PostRaw
from app.models.task import Task, TaskStatus
from app.models.tier_suggestion import TierSuggestion
from app.utils.url import normalize_reddit_url


_OPS_NAMESPACE = uuid.UUID("d4b6c11d-2a8d-4c60-8fd3-7c2a4b3f2d9e")


@dataclass(slots=True)
class TierSuggestionDecisionUnitEmissionResult:
    task_id: uuid.UUID
    created_units: int
    skipped_existing_units: int
    created_evidences: int


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _task_id_for_day(*, user_id: uuid.UUID, day: datetime) -> uuid.UUID:
    day_key = _ensure_utc(day).date().isoformat()
    return uuid.uuid5(_OPS_NAMESPACE, f"ops:tier_suggestions:{user_id}:{day_key}")


def _decision_unit_id_for_suggestion(*, user_id: uuid.UUID, suggestion_id: int) -> uuid.UUID:
    return uuid.uuid5(_OPS_NAMESPACE, f"ops:tier_suggestion:{user_id}:{suggestion_id}")


def _build_summary(reasons: list[str] | None) -> str:
    cleaned = [r.strip() for r in (reasons or []) if str(r).strip()]
    if not cleaned:
        return "调级建议（暂无理由明细）"
    return "；".join(cleaned[:3])[:2000]


def _build_excerpt(*, title: str | None, body: str | None, max_len: int = 900) -> str:
    parts = []
    if title and title.strip():
        parts.append(title.strip())
    if body and body.strip():
        parts.append(body.strip())
    text = "\n".join(parts).strip()
    if not text:
        return "（无可用内容摘录）"
    return text[:max_len]


async def emit_tier_suggestions_as_decision_units(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    suggestion_ids: Sequence[int] | None = None,
    suggestions: Sequence[TierSuggestion] | None = None,
    emitted_at: datetime | None = None,
    lookback_days: int = 30,
    max_evidence_posts: int = 3,
) -> TierSuggestionDecisionUnitEmissionResult:
    """
    Convert tier_suggestions into ops DecisionUnits.

    大白话：
    - 这一步只是在“把建议翻译成可复用的决策单元”，不改变 tier_suggestions 的状态。
    - 失败不应该影响主业务链路（由调用方按 best-effort 包一层 try/except）。
    """

    if emitted_at is None:
        emitted_at = datetime.now(timezone.utc)
    emitted_at = _ensure_utc(emitted_at)

    if lookback_days <= 0:
        lookback_days = 1
    if max_evidence_posts <= 0:
        max_evidence_posts = 1

    resolved: list[TierSuggestion]
    if suggestions is not None:
        resolved = list(suggestions)
    elif suggestion_ids:
        result = await session.execute(
            select(TierSuggestion).where(TierSuggestion.id.in_(list(suggestion_ids)))
        )
        resolved = list(result.scalars().all())
    else:
        resolved = []

    task_id = _task_id_for_day(user_id=user_id, day=emitted_at)
    task = await session.get(Task, task_id)
    if task is None:
        task = Task(
            id=task_id,
            user_id=user_id,
            product_description=f"ops: tier suggestions decision units ({emitted_at.date().isoformat()})",
            mode="operations",
            audit_level="gold",
            status=TaskStatus.COMPLETED,
            started_at=emitted_at,
            completed_at=emitted_at,
        )
        session.add(task)
        await session.flush()

    created_units = 0
    skipped_existing = 0
    created_evidences = 0

    for sugg in resolved:
        du_id = _decision_unit_id_for_suggestion(user_id=user_id, suggestion_id=sugg.id)
        existing = await session.get(InsightCard, du_id)
        if existing is not None:
            skipped_existing += 1
            continue

        claim = f"把 {sugg.community_name} 从 {sugg.current_tier} 调到 {sugg.suggested_tier}"
        title = f"调级建议：{sugg.community_name} {sugg.current_tier}→{sugg.suggested_tier} (s{sugg.id})"

        du_payload = {
            "claim": claim,
            "reasons": list(sugg.reasons or []),
            "metrics": dict(sugg.metrics or {}),
            "recommended_actions": [
                {
                    "type": "community_tier_change",
                    "community": sugg.community_name,
                    "from": sugg.current_tier,
                    "to": sugg.suggested_tier,
                    "suggestion_id": sugg.id,
                }
            ],
            "versions": {
                "du_schema_version": 1,
                "generator": "tier_intelligence",
            },
            "lineage": {
                "source": "tier_suggestions",
                "suggestion_id": sugg.id,
                "generated_at": _ensure_utc(sugg.generated_at).isoformat(),
                "expires_at": _ensure_utc(sugg.expires_at).isoformat(),
                "status": sugg.status,
            },
        }

        card = InsightCard(
            id=du_id,
            task_id=task_id,
            kind="decision_unit",
            signal_type="ops",
            du_schema_version=1,
            du_payload=du_payload,
            title=title,
            summary=_build_summary(list(sugg.reasons or [])),
            confidence=float(sugg.confidence),
            time_window_days=lookback_days,
            subreddits=[sugg.community_name],
        )
        session.add(card)
        created_units += 1

        # Evidence: pick top engagement posts from the suggested community (simple + cheap).
        subreddit_clean = str(sugg.community_name or "").replace("r/", "")
        subreddits_to_query = [f"r/{subreddit_clean}", subreddit_clean]
        cutoff = emitted_at - timedelta(days=lookback_days)

        posts = (
            await session.execute(
                select(PostRaw)
                .where(
                    PostRaw.subreddit.in_(subreddits_to_query),
                    PostRaw.created_at >= cutoff,
                    PostRaw.is_current.is_(True),
                )
                .order_by(desc(PostRaw.score + PostRaw.num_comments), desc(PostRaw.created_at))
                .limit(max_evidence_posts)
            )
        ).scalars().all()

        for idx, post in enumerate(posts):
            meta = getattr(post, "extra_data", None) or {}
            permalink = meta.get("permalink") if isinstance(meta, dict) else None
            post_url = normalize_reddit_url(url=getattr(post, "url", None), permalink=permalink)
            evidence_score = max(0.1, round(1.0 - (idx * 0.1), 2))
            evidence = Evidence(
                insight_card_id=du_id,
                post_url=post_url,
                excerpt=_build_excerpt(title=getattr(post, "title", None), body=getattr(post, "body", None)),
                timestamp=_ensure_utc(post.created_at),
                subreddit=str(post.subreddit or sugg.community_name),
                score=evidence_score,
                content_type="post",
                content_id=int(post.id),
            )
            session.add(evidence)
            created_evidences += 1

    await session.commit()

    return TierSuggestionDecisionUnitEmissionResult(
        task_id=task_id,
        created_units=created_units,
        skipped_existing_units=skipped_existing,
        created_evidences=created_evidences,
    )


__all__ = [
    "TierSuggestionDecisionUnitEmissionResult",
    "emit_tier_suggestions_as_decision_units",
]

