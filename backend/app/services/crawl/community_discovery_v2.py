"""社区自动发现（Semantic Discovery Radar）.

基于痛点关键词，调用 Reddit 搜索发现新社区，结合 Tier 指标筛选。
"""
from __future__ import annotations

import asyncio
import logging
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analysis.deduplicator import deduplicate_posts
from app.services.infrastructure.reddit_client import RedditAPIClient
from app.services.analysis.t1_clustering import build_pain_clusters
from app.services.analysis.tier_intelligence import TierIntelligenceService
from app.services.community.blacklist_loader import BlacklistConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiscoveryResult:
    name: str
    subscribers: int
    pain_density: float
    description: str
    source_keyword: str
    reason: str


class CommunityDiscoveryService:
    """通过痛点关键词自动发现新社区."""

    def __init__(
        self,
        db: AsyncSession,
        reddit_client: RedditAPIClient,
        *,
        blacklist: BlacklistConfig | None = None,
        min_pain_density: float = 0.10,
        lookback_days: int = 90,
    ) -> None:
        self.db = db
        self.reddit_client = reddit_client
        self.blacklist = blacklist
        self.min_pain_density = min_pain_density
        self.lookback_days = lookback_days
        self.tier_service = TierIntelligenceService(db)

    async def extract_pain_keywords(
        self, *, top_k: int = 10, days: int | None = None
    ) -> list[str]:
        """从历史痛点聚类里提取高频关键词."""
        clusters = await build_pain_clusters(
            self.db, days=days or self.lookback_days, sample_per_aspect=8
        )
        counter: Counter[str] = Counter()
        for c in clusters:
            counter.update(c.keywords)
        return [kw for kw, _ in counter.most_common(top_k)]

    async def discover_by_keywords(
        self,
        keywords: Sequence[str],
        *,
        limit_per_kw: int = 10,
        include_nsfw: bool = False,
    ) -> list[DiscoveryResult]:
        """搜索并过滤社区，按 pain_density>阈值 过滤."""
        seen: set[str] = set()
        candidates: list[DiscoveryResult] = []

        for kw in keywords:
            try:
                subs = await self.reddit_client.search_subreddits(
                    kw, limit=limit_per_kw, include_nsfw=include_nsfw
                )
            except Exception as exc:
                logger.warning("Search failed for kw=%s: %s", kw, exc)
                continue

            for item in subs:
                name = str(item.get("name") or "").lower()
                if not name or name in seen:
                    continue
                seen.add(name)

                if self.blacklist and self.blacklist.is_community_blacklisted(name):
                    logger.debug("Skip blacklisted community: %s", name)
                    continue

                # 计算 pain_density，过滤低信号社区
                try:
                    metrics = await self.tier_service.calculate_community_metrics(
                        name, lookback_days=self.lookback_days
                    )
                    pain_density = float(metrics.pain_density or 0.0)
                except Exception:
                    logger.exception("calculate_community_metrics failed for %s", name)
                    pain_density = 0.0

                if pain_density < self.min_pain_density:
                    continue

                candidates.append(
                    DiscoveryResult(
                        name=name,
                        subscribers=int(item.get("subscribers") or 0),
                        pain_density=round(pain_density, 4),
                        description=item.get("public_description") or "",
                        source_keyword=kw,
                        reason="pain_density>=threshold",
                    )
                )

        # 去重（同名社区）后按 pain_density/subscribers 排序
        enriched = [
            {
                "id": cand.name,
                "title": cand.name,
                "summary": f"{cand.description} pain={cand.pain_density}",
                "score": cand.pain_density,
                "num_comments": cand.subscribers,
            }
            for cand in candidates
        ]
        deduped = deduplicate_posts(enriched, threshold=None)
        deduped_names = {item["id"] for item in deduped}
        filtered = [c for c in candidates if c.name in deduped_names]

        filtered.sort(
            key=lambda c: (c.pain_density, c.subscribers),
            reverse=True,
        )
        return filtered


__all__ = ["CommunityDiscoveryService", "DiscoveryResult"]
