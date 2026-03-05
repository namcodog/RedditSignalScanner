"""基于痛点密度的自适应调度器."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analysis.tier_intelligence import CommunityMetrics, TierIntelligenceService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PriorityEntry:
    name: str
    priority_score: float
    pain_density: float
    posts_per_day: float
    surge: bool


class AdaptiveScheduler:
    """按 Pain Density 加权的抓取优先级计算."""

    def __init__(self, db: AsyncSession, *, lookback_days: int = 30) -> None:
        self.db = db
        self.lookback_days = lookback_days
        self.tier_service = TierIntelligenceService(db)

    async def rank(
        self, communities: Sequence[str]
    ) -> Tuple[list[str], list[PriorityEntry]]:
        entries: list[PriorityEntry] = []
        for name in communities:
            try:
                metrics = await self.tier_service.calculate_community_metrics(
                    name, lookback_days=self.lookback_days
                )
                entry = self._build_entry(name, metrics)
                entries.append(entry)
            except Exception:
                logger.exception("Failed to compute metrics for %s", name)

        if not entries:
            return list(communities), []

        entries.sort(key=lambda e: e.priority_score, reverse=True)
        ordered = [e.name for e in entries]
        return ordered, entries

    def _build_entry(self, name: str, metrics: CommunityMetrics) -> PriorityEntry:
        pain_density = float(metrics.pain_density or 0.0)
        posts_per_day = float(metrics.posts_per_day or 0.0)
        priority_score = (posts_per_day * 0.3) + (pain_density * 0.7)

        surge = False
        trend = metrics.pain_trend_30d or []
        if trend:
            latest = float(trend[-1] or 0.0)
            avg = (
                sum(float(x or 0.0) for x in trend) / max(1, len(trend))
            )
            if avg > 0 and latest >= 2 * avg:
                surge = True
                priority_score *= 1.2

        return PriorityEntry(
            name=name,
            priority_score=round(priority_score, 4),
            pain_density=round(pain_density, 4),
            posts_per_day=round(posts_per_day, 4),
            surge=surge,
        )


__all__ = ["AdaptiveScheduler", "PriorityEntry"]
