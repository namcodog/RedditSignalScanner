from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.insight import InsightCard
from app.models.task import Task
from app.schemas.insight import (
    EvidenceItem,
    InsightCardListResponse,
    InsightCardResponse,
)


class TaskNotFoundError(RuntimeError):
    """Raised when the requested task does not exist."""


class TaskAccessDeniedError(RuntimeError):
    """Raised when a user tries to access a task they do not own."""


class InsightNotFoundError(RuntimeError):
    """Raised when the requested insight card does not exist for the user."""


@dataclass(slots=True)
class InsightFilters:
    """Filters for querying insight cards."""

    min_confidence: float | None = None
    subreddit: str | None = None
    limit: int = 10
    offset: int = 0


class InsightService:
    """Service layer for retrieving insight cards and evidence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_task(
        self,
        *,
        task_id: UUID,
        user_id: UUID,
        filters: InsightFilters,
    ) -> InsightCardListResponse:
        task = await self._session.get(Task, task_id)
        if task is None:
            raise TaskNotFoundError
        if task.user_id != user_id:
            raise TaskAccessDeniedError

        base_query = (
            select(InsightCard)
            .options(
                joinedload(InsightCard.evidences),
                joinedload(InsightCard.task),
            )
            .where(InsightCard.task_id == task_id)
        )

        count_query = select(func.count(InsightCard.id)).where(
            InsightCard.task_id == task_id
        )

        if filters.min_confidence is not None:
            base_query = base_query.where(
                InsightCard.confidence >= filters.min_confidence
            )
            count_query = count_query.where(
                InsightCard.confidence >= filters.min_confidence
            )

        if filters.subreddit is not None and filters.subreddit.strip():
            normalized = filters.subreddit.strip()
            base_query = base_query.where(
                InsightCard.subreddits.contains([normalized])
            )
            count_query = count_query.where(
                InsightCard.subreddits.contains([normalized])
            )

        total_result = await self._session.execute(count_query)
        total = int(total_result.scalar_one() or 0)

        if total == 0:
            # 兜底策略：基于 Analysis.insights 动态生成卡片响应，保证前端可见性
            try:
                from app.services.report_service import ReportService
                service = ReportService(self._session)
                payload = await service.get_report(task_id, user_id)
                synthetic: list[InsightCardResponse] = []
                # 优先从 opportunities 构建卡片，其次 pain_points；最后从 action_items 兜底
                # 术语规范化工具
                def _norm_text(s: str) -> str:
                    try:
                        import yaml  # type: ignore
                        from pathlib import Path
                        m = {}
                        f = Path("backend/config/phrase_mapping.yml")
                        if f.exists():
                            m = yaml.safe_load(f.read_text(encoding='utf-8')) or {}
                        for k, v in m.items():
                            s = s.replace(k, v)
                    except Exception:
                        return s
                    return s

                def _build_from_entries(entries):
                    nonlocal synthetic
                    for entry in entries[: filters.limit - len(synthetic)]:
                        title_raw = str(getattr(entry, 'description', None) or getattr(entry, 'title', None) or getattr(entry, 'problem_definition', None) or "洞察")
                        summary_raw = str(getattr(entry, 'summary', None) or title_raw)
                        title = _norm_text(title_raw)
                        summary = _norm_text(summary_raw)
                        conf = float(getattr(entry, 'confidence', 0.9) or 0.9)
                        subs = []
                        ev_list = []
                        # 尝试从 entry.example_posts
                        ep = getattr(entry, 'example_posts', None) or []
                        for p in ep[:3]:
                            sub = str(getattr(p, 'community', None) or p.get('community') if isinstance(p, dict) else '')
                            if sub and sub not in subs:
                                subs.append(sub)
                            url = str(getattr(p, 'url', None) or getattr(p, 'permalink', None) or (p.get('url') if isinstance(p, dict) else '') or '')
                            excerpt = str(getattr(p, 'content', None) or (p.get('content') if isinstance(p, dict) else '') or '')
                            ev_list.append(EvidenceItem(id=UUID(int=0), post_id=None, post_url=url, excerpt=excerpt, timestamp=None, subreddit=sub or '', score=None))
                        synthetic.append(InsightCardResponse(
                            id=UUID(int=0), task_id=task_id, title=title, summary=summary,
                            confidence=conf, time_window=self._format_time_window(30), time_window_days=30,
                            subreddits=subs, evidence=ev_list, created_at=payload.generated_at, updated_at=payload.generated_at
                        ))

                _build_from_entries(list(payload.report.opportunities or []))
                if len(synthetic) < filters.limit:
                    _build_from_entries(list(payload.report.pain_points or []))
                if len(synthetic) < filters.limit:
                    _build_from_entries(list(payload.report.action_items or []))

                if synthetic:
                    return InsightCardListResponse(total=len(synthetic), items=synthetic)
            except Exception:
                pass

        result = await self._session.execute(
            base_query.order_by(InsightCard.created_at.desc())
            .limit(filters.limit)
            .offset(filters.offset)
        )
        cards: Sequence[InsightCard] = result.scalars().unique().all()

        items = [self._to_response(card) for card in cards]
        return InsightCardListResponse(total=total, items=items)

    async def get_by_id(self, *, insight_id: UUID, user_id: UUID) -> InsightCardResponse:
        query = (
            select(InsightCard)
            .options(
                joinedload(InsightCard.evidences),
                joinedload(InsightCard.task),
            )
            .where(InsightCard.id == insight_id)
        )

        result = await self._session.execute(query)
        card = result.unique().scalar_one_or_none()
        if card is None:
            raise InsightNotFoundError
        if card.task.user_id != user_id:
            raise TaskAccessDeniedError

        return self._to_response(card)

    @staticmethod
    def _format_time_window(days: int) -> str:
        if days <= 0:
            return "未知时间窗口"
        return f"过去 {days} 天"

    def _to_response(self, card: InsightCard) -> InsightCardResponse:
        evidence_items = [
            EvidenceItem(
                id=evidence.id,
                post_id=None,
                post_url=evidence.post_url,
                excerpt=evidence.excerpt,
                timestamp=evidence.timestamp,
                subreddit=evidence.subreddit,
                score=float(evidence.score) if evidence.score is not None else None,
            )
            for evidence in card.evidences
        ]

        return InsightCardResponse(
            id=card.id,
            task_id=card.task_id,
            title=card.title,
            summary=card.summary,
            confidence=float(card.confidence),
            time_window=self._format_time_window(card.time_window_days),
            time_window_days=card.time_window_days,
            subreddits=card.subreddits,
            evidence=evidence_items,
            created_at=card.created_at,
            updated_at=card.updated_at,
        )


__all__ = [
    "InsightFilters",
    "InsightNotFoundError",
    "InsightService",
    "TaskAccessDeniedError",
    "TaskNotFoundError",
]
