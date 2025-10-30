from __future__ import annotations

import asyncio
import copy
import logging
import time
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.task import Task, TaskStatus
from app.models.user import MembershipLevel
from app.repositories.report_repository import ReportRepository
from app.schemas.analysis import (
    AnalysisRead,
    CommunitySourceDetail,
    InsightsPayload,
    OpportunityReportOut,
    SourcesPayload,
)
from app.schemas.report_payload import (
    FallbackQuality,
    ReportContent,
    ReportExecutiveSummary,
    ReportMetadata,
    ReportOverview,
    ReportPayload,
    ReportStats,
    SentimentBreakdown,
    TopCommunity,
)
from app.services.reporting.opportunity_report import build_opportunity_reports

logger = logging.getLogger(__name__)


class ReportServiceError(Exception):
    """Base class for service-layer errors."""

    status_code: int = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ReportNotFoundError(ReportServiceError):
    status_code = 404


class ReportAccessDeniedError(ReportServiceError):
    status_code = 403


class ReportNotReadyError(ReportServiceError):
    status_code = 409


class ReportDataValidationError(ReportServiceError):
    status_code = 500


@dataclass(slots=True)
class ReportServiceConfig:
    community_members: dict[str, int]
    cache_ttl_seconds: int
    target_analysis_version: str


class ReportCacheProtocol(Protocol):
    async def get(self, key: str) -> ReportPayload | None:
        ...

    async def set(self, key: str, value: ReportPayload) -> None:
        ...

    async def invalidate(self, key: str) -> None:
        ...


class InMemoryReportCache(ReportCacheProtocol):
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = max(1, ttl_seconds)
        self._store: dict[str, tuple[float, ReportPayload]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> ReportPayload | None:
        async with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, payload = entry
            if expires_at <= time.monotonic():
                self._store.pop(key, None)
                return None
            return payload.model_copy(deep=True)

    async def set(self, key: str, value: ReportPayload) -> None:
        async with self._lock:
            self._store[key] = (
                time.monotonic() + self._ttl_seconds,
                value.model_copy(deep=True),
            )

    async def invalidate(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)


class ReportService:
    """Business logic for assembling the report analysis payload."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        config: ReportServiceConfig | None = None,
        cache: ReportCacheProtocol | None = None,
        repository: ReportRepository | None = None,
    ) -> None:
        resolved_config = config or ReportServiceConfig(
            community_members=settings.report_community_members,
            cache_ttl_seconds=settings.report_cache_ttl_seconds,
            target_analysis_version=settings.report_target_analysis_version,
        )
        self._config = resolved_config
        self._repository = repository or ReportRepository(db)
        self._cache = cache or InMemoryReportCache(resolved_config.cache_ttl_seconds)

    async def get_report(self, task_id: UUID, user_id: UUID) -> ReportPayload:
        task = await self._repository.get_task_with_analysis(task_id)
        if task is None:
            raise ReportNotFoundError("Task not found")

        if task.user_id != user_id:
            raise ReportAccessDeniedError("Not authorised to access this task")

        if task.status != TaskStatus.COMPLETED:
            raise ReportNotReadyError("Task has not completed yet")

        if task.analysis is None:
            raise ReportNotFoundError("Analysis not found")

        analysis = task.analysis
        if analysis.report is None:
            raise ReportNotFoundError("Report not found")

        user_membership = (
            task.user.membership_level if task.user else MembershipLevel.FREE
        )
        if user_membership not in {MembershipLevel.PRO, MembershipLevel.ENTERPRISE}:
            raise ReportAccessDeniedError(
                "Your subscription tier does not include report access"
            )

        cache_key = f"report:{task_id}:{user_id}"
        if self._cache:
            cached = await self._cache.get(cache_key)
            if (
                cached is not None
                and cached.generated_at == analysis.report.generated_at
            ):
                logger.debug("Cache hit for report task %s", task_id)
                return cached

        analysis_payload = self._validate_analysis_payload(analysis)

        action_items = analysis_payload.insights.action_items
        if not action_items:
            generated = build_opportunity_reports(
                analysis_payload.insights.model_dump(mode="json")
            )
            action_items = [
                OpportunityReportOut.model_validate(item.to_dict())
                for item in generated
            ]

        # P1: 证据密度约束（每条行动项至少2条可点击证据URL），不足则降级标注
        insufficient_evidence_detected = False
        normalized_items: list[OpportunityReportOut] = []
        for item in action_items:
            try:
                url_count = sum(1 for ev in (item.evidence_chain or []) if getattr(ev, "url", None))
                if url_count < 2:
                    insufficient_evidence_detected = True
                    # 降级标注（不改变结构，只追加一条提示到建议动作）
                    tips = list(item.suggested_actions or [])
                    marker = f"证据不足(n<2)"
                    if marker not in tips:
                        tips.append(marker)
                    item = OpportunityReportOut(
                        problem_definition=item.problem_definition,
                        evidence_chain=item.evidence_chain,
                        suggested_actions=tips,
                        confidence=item.confidence,
                        urgency=item.urgency,
                        product_fit=item.product_fit,
                        priority=item.priority,
                    )
            except Exception:
                pass
            normalized_items.append(item)
        action_items = normalized_items

        stats = self._build_stats(analysis_payload)
        overview = await self._build_overview(
            analysis_payload.sources.communities_detail or [], stats
        )
        summary = self._build_summary(
            analysis_payload.insights, analysis_payload.sources
        )
        metadata = self._build_metadata(
            task,
            analysis_payload,
            analysis.report.generated_at,
            stats,
        )

        # 统计一致性与降级标注：如 overview 百分比与 stats 总量不自洽，则记录 recovery 标记
        try:
            pct_sum = overview.sentiment.positive + overview.sentiment.negative + overview.sentiment.neutral
            # 允许四舍五入误差（±2）
            recovery_reasons: list[str] = []
            if pct_sum < 98 or pct_sum > 102:
                recovery_reasons.append("stats_inconsistency")
            if insufficient_evidence_detected:
                recovery_reasons.append("insufficient_evidence")
            if recovery_reasons:
                # 合并到 sources.recovery_strategy，便于前端或日志定位
                existing = (analysis_payload.sources.recovery_strategy or "").strip()
                merged = ",".join(filter(None, [existing] + recovery_reasons)).strip(",")
                analysis_payload.sources.recovery_strategy = merged or None
                metadata.recovery_applied = merged or None
        except Exception:
            # 保守处理，不影响主流程
            pass

        # 术语与措辞规范化（基于可选映射表），仅作用于可读文案，不改动原始数据统计
        def _normalize_text(s: Any) -> Any:
            if not isinstance(s, str):
                return s
            try:
                import yaml  # type: ignore
                from pathlib import Path
                mapping_file = Path("backend/config/phrase_mapping.yml")
                mapping: dict[str, str] = {}
                if mapping_file.exists():
                    mapping = yaml.safe_load(mapping_file.read_text(encoding="utf-8")) or {}
                for k, v in mapping.items():
                    s = s.replace(k, v)
            except Exception:
                # 忽略映射加载错误
                return s
            return s

        # 对 action_items 与 pain_points/opportunities 的可读字段做轻量规范化
        for item in action_items:
            try:
                if hasattr(item, "problem_definition") and item.problem_definition:
                    item.problem_definition = _normalize_text(item.problem_definition)
                if hasattr(item, "suggested_actions") and item.suggested_actions:
                    item.suggested_actions = [
                        _normalize_text(a) for a in item.suggested_actions
                    ]
            except Exception:
                continue

        for col in (analysis_payload.insights.pain_points, analysis_payload.insights.opportunities):
            for obj in col:
                try:
                    if hasattr(obj, "description") and obj.description:
                        obj.description = _normalize_text(obj.description)
                except Exception:
                    continue

        payload = ReportPayload(
            task_id=task.id,
            status=task.status,
            generated_at=analysis.report.generated_at,
            product_description=analysis_payload.sources.product_description
            or task.product_description,
            report=ReportContent(
                executive_summary=summary,
                pain_points=analysis_payload.insights.pain_points,
                competitors=analysis_payload.insights.competitors,
                opportunities=analysis_payload.insights.opportunities,
                action_items=action_items,
                entity_summary=analysis_payload.insights.entity_summary,
            ),
            metadata=metadata,
            overview=overview,
            stats=stats,
            report_html=analysis.report.html_content,
        )

        logger.debug(
            "Generated report payload for task %s (status=%s)",
            task.id,
            task.status,
        )
        if self._cache:
            await self._cache.set(cache_key, payload)
        return payload

    def _validate_analysis_payload(self, analysis: Any) -> AnalysisRead:
        raw_insights = copy.deepcopy(analysis.insights or {})
        raw_sources = copy.deepcopy(analysis.sources or {})
        (
            migrated_insights,
            migrated_sources,
            resolved_version,
        ) = self._apply_version_migrations(
            str(analysis.analysis_version), raw_insights, raw_sources
        )
        processed_insights = self._normalise_insights(migrated_insights)
        processed_sources = self._normalise_sources(migrated_sources)

        payload = {
            "id": analysis.id,
            "task_id": analysis.task_id,
            "insights": processed_insights,
            "sources": processed_sources,
            "confidence_score": analysis.confidence_score,
            "analysis_version": resolved_version,
            "created_at": analysis.created_at,
        }

        try:
            return AnalysisRead.model_validate(payload)
        except ValidationError as exc:
            logger.exception(
                "Analysis payload validation failed for analysis=%s", analysis.id
            )
            raise ReportDataValidationError(
                "Failed to validate analysis payload"
            ) from exc

    def _normalise_insights(self, insights: dict[str, Any]) -> dict[str, Any]:
        pain_points = insights.get("pain_points") or []
        for item in pain_points:
            sentiment = float(item.get("sentiment_score", 0.0))
            # Clamp sentiment_score to [-1.0, 1.0] range
            item["sentiment_score"] = max(-1.0, min(1.0, sentiment))
            if not item.get("severity"):
                item["severity"] = self._classify_severity(sentiment)
            item.setdefault("example_posts", [])
            item.setdefault("user_examples", [])

        insights.setdefault("pain_points", pain_points)
        insights.setdefault("competitors", insights.get("competitors") or [])
        insights.setdefault("opportunities", insights.get("opportunities") or [])
        insights.setdefault("action_items", insights.get("action_items") or [])
        current_summary = insights.get("entity_summary") or {}
        insights.setdefault(
            "entity_summary",
            {
                "brands": current_summary.get("brands", []),
                "features": current_summary.get("features", []),
                "pain_points": current_summary.get("pain_points", []),
            },
        )
        return insights

    @staticmethod
    def _classify_severity(sentiment_score: float) -> str:
        if sentiment_score <= -0.6:
            return "high"
        if sentiment_score <= -0.3:
            return "medium"
        return "low"

    def _normalise_sources(self, sources: dict[str, Any]) -> dict[str, Any]:
        sources.setdefault("communities", [])
        sources.setdefault("posts_analyzed", 0)
        sources.setdefault("cache_hit_rate", 0.0)
        sources.setdefault("analysis_duration_seconds", None)
        sources.setdefault("reddit_api_calls", None)
        sources.setdefault("product_description", None)
        sources.setdefault("communities_detail", [])
        return sources

    def _apply_version_migrations(
        self,
        version: str,
        insights: dict[str, Any],
        sources: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        current = self._format_analysis_version(version)
        target = self._format_analysis_version(self._config.target_analysis_version)
        migrations: dict[str, Any] = {
            "0.9": self._migrate_v09_to_v10,
        }

        visited: set[str] = set()
        updated_insights = insights
        updated_sources = sources

        while current in migrations and current != target and current not in visited:
            visited.add(current)
            migrator = migrations[current]
            logger.info("Migrating analysis payload from version %s", current)
            updated_insights, updated_sources, current = migrator(
                updated_insights, updated_sources
            )

        return updated_insights, updated_sources, current

    def _migrate_v09_to_v10(
        self, insights: dict[str, Any], sources: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        migrated_insights = copy.deepcopy(insights)
        for item in migrated_insights.get("pain_points", []) or []:
            sentiment = float(item.get("sentiment_score", 0.0))
            item.setdefault("severity", self._classify_severity(sentiment))
            item.setdefault("example_posts", [])
            item.setdefault("user_examples", [])

        migrated_sources = copy.deepcopy(sources)
        if (
            "analysis_duration" in migrated_sources
            and migrated_sources.get("analysis_duration_seconds") is None
        ):
            migrated_sources["analysis_duration_seconds"] = migrated_sources[
                "analysis_duration"
            ]

        return migrated_insights, migrated_sources, "1.0"

    def _build_stats(self, analysis: AnalysisRead) -> ReportStats:
        pain_points = analysis.insights.pain_points
        competitors = analysis.insights.competitors

        positive_mentions = sum(
            item.frequency for item in pain_points if item.sentiment_score > 0.05
        ) + sum(
            comp.mentions
            for comp in competitors
            if str(comp.sentiment).lower() == "positive"
        )
        negative_mentions = sum(
            item.frequency for item in pain_points if item.sentiment_score < -0.05
        ) + sum(
            comp.mentions
            for comp in competitors
            if str(comp.sentiment).lower() == "negative"
        )
        # 初始以 posts_analyzed 为参考，若不可信则回退到自洽口径
        neutral_candidates = analysis.sources.posts_analyzed - positive_mentions - negative_mentions
        neutral_mentions = max(0, neutral_candidates)

        # 强制总和自洽：total = pos + neg + neu
        pos = max(int(positive_mentions), 0)
        neg = max(int(negative_mentions), 0)
        neu = max(int(neutral_mentions), 0)
        total = pos + neg + neu

        # 如 posts_analyzed 明显小于 pos+neg，则记入恢复策略由上层标注
        return ReportStats(
            total_mentions=total,
            positive_mentions=pos,
            negative_mentions=neg,
            neutral_mentions=neu,
        )

    async def _get_community_member_count(self, community_name: str) -> int:
        """Get member count for a community from database or fallback to config.

        Args:
            community_name: Community name (e.g., 'r/startups')

        Returns:
            Member count (from DB, config, or default 100,000)
        """
        from sqlalchemy import select

        from app.models.community_cache import CommunityCache

        # Try to get from database first
        try:
            result = await self._repository._db.execute(
                select(CommunityCache.member_count).where(
                    CommunityCache.community_name == community_name
                )
            )
            member_count = result.scalar_one_or_none()

            if member_count is not None and member_count > 0:
                logger.debug(
                    f"Using DB member count for {community_name}: {member_count:,}"
                )
                return member_count
        except Exception as e:
            logger.warning(
                f"Failed to fetch member count from DB for {community_name}: {e}"
            )

        # Fallback to config
        config_count = self._config.community_members.get(community_name.lower())
        if config_count:
            logger.debug(
                f"Using config member count for {community_name}: {config_count:,}"
            )
            return config_count

        # Final fallback to default
        logger.debug(f"Using default member count for {community_name}: 100,000")
        return 100_000

    async def _build_overview(
        self,
        communities_detail: list[CommunitySourceDetail],
        stats: ReportStats,
    ) -> ReportOverview:
        total = max(stats.total_mentions, 1)
        # Calculate percentages and ensure they sum to 100
        positive_pct = stats.positive_mentions / total * 100
        negative_pct = stats.negative_mentions / total * 100
        neutral_pct = stats.neutral_mentions / total * 100

        # Round and clamp to ensure valid range [0, 100]
        positive = max(0, min(100, int(round(positive_pct))))
        negative = max(0, min(100, int(round(negative_pct))))
        neutral = max(0, min(100, int(round(neutral_pct))))

        # Adjust to ensure sum doesn't exceed 100
        total_pct = positive + negative + neutral
        if total_pct > 100:
            # Reduce the largest component
            if positive >= negative and positive >= neutral:
                positive -= (total_pct - 100)
            elif negative >= neutral:
                negative -= (total_pct - 100)
            else:
                neutral -= (total_pct - 100)

        sentiment = SentimentBreakdown(
            positive=max(0, positive),
            negative=max(0, negative),
            neutral=max(0, neutral),
        )

        # Build top communities with member counts from DB
        top_communities = []
        # 社区治理：过滤黑名单社区，避免噪音出现在 Top 列
        filtered_details = communities_detail
        try:
            from app.services.blacklist_loader import get_blacklist_config
            bl = get_blacklist_config()
            filtered_details = [d for d in communities_detail if not bl.is_community_blacklisted(d.name)] or communities_detail
        except Exception:
            filtered_details = communities_detail
        for detail in sorted(
            filtered_details,
            key=lambda item: item.mentions,
            reverse=True,
        )[:5]:
            member_count = await self._get_community_member_count(detail.name)
            top_communities.append(
                TopCommunity(
                    name=detail.name,
                    mentions=detail.mentions,
                    relevance=int(round(detail.cache_hit_rate * 100)),
                    category=(detail.categories or [None])[0],
                    daily_posts=detail.daily_posts,
                    avg_comment_length=detail.avg_comment_length,
                    from_cache=detail.from_cache,
                    members=member_count,
                )
            )

        # Header helpers
        total_communities = len(communities_detail)
        top_n = len(top_communities)
        # 推断来源：若任一条 detail.categories 包含 "discovered"，认为来源包含 discovery
        seed_source = None
        try:
            if any("discovered" in (d.categories or []) for d in communities_detail):
                seed_source = "pool+discovery"
            elif communities_detail:
                seed_source = "pool"
        except Exception:
            seed_source = None

        return ReportOverview(
            sentiment=sentiment,
            top_communities=top_communities,
            total_communities=total_communities,
            top_n=top_n,
            seed_source=seed_source,
        )

    def _build_summary(
        self,
        insights: InsightsPayload,
        sources: SourcesPayload,
    ) -> ReportExecutiveSummary:
        key_insights = (
            len(insights.pain_points)
            + len(insights.competitors)
            + len(insights.opportunities)
        )
        top_opportunity = (
            insights.opportunities[0].description if insights.opportunities else ""
        )
        return ReportExecutiveSummary(
            total_communities=len(sources.communities),
            key_insights=key_insights,
            top_opportunity=top_opportunity,
        )

    def _build_metadata(
        self,
        task: Task,
        analysis: AnalysisRead,
        generated_at: Any,
        stats: ReportStats,
    ) -> ReportMetadata:
        processing_seconds = analysis.sources.analysis_duration_seconds
        if processing_seconds is None and generated_at is not None:
            processing_seconds = max(
                0.0,
                float((generated_at - analysis.created_at).total_seconds()),
            )

        fallback_quality = None
        if analysis.sources.fallback_quality:
            fallback_quality = FallbackQuality.model_validate(
                analysis.sources.fallback_quality
            )

        return ReportMetadata(
            analysis_version=self._format_analysis_version(analysis.analysis_version),
            confidence_score=float(analysis.confidence_score or 0.0),
            processing_time_seconds=float(processing_seconds or 0.0),
            cache_hit_rate=float(analysis.sources.cache_hit_rate or 0.0),
            total_mentions=stats.total_mentions,
            recovery_applied=analysis.sources.recovery_strategy,
            fallback_quality=fallback_quality,
        )

    @staticmethod
    def _format_analysis_version(version: Any) -> str:
        try:
            numeric = float(version)
        except (TypeError, ValueError):
            return str(version)
        if numeric.is_integer():
            return f"{numeric:.1f}"
        return str(numeric)


__all__ = [
    "InMemoryReportCache",
    "ReportAccessDeniedError",
    "ReportCacheProtocol",
    "ReportDataValidationError",
    "ReportNotFoundError",
    "ReportNotReadyError",
    "ReportService",
    "ReportServiceConfig",
    "ReportServiceError",
]
