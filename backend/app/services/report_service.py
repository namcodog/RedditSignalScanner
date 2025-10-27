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
            self._store[key] = (time.monotonic() + self._ttl_seconds, value.model_copy(deep=True))

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

        user_membership = task.user.membership_level if task.user else MembershipLevel.FREE
        if user_membership not in {MembershipLevel.PRO, MembershipLevel.ENTERPRISE}:
            raise ReportAccessDeniedError("Your subscription tier does not include report access")

        cache_key = f"report:{task_id}:{user_id}"
        if self._cache:
            cached = await self._cache.get(cache_key)
            if cached is not None and cached.generated_at == analysis.report.generated_at:
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

        payload = ReportPayload(
            task_id=task.id,
            status=task.status,
            generated_at=analysis.report.generated_at,
            product_description=
            analysis_payload.sources.product_description
            or task.product_description,
            report=ReportContent(
                executive_summary=summary,
                pain_points=analysis_payload.insights.pain_points,
                competitors=analysis_payload.insights.competitors,
                opportunities=analysis_payload.insights.opportunities,
                action_items=action_items,
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
        migrated_insights, migrated_sources, resolved_version = self._apply_version_migrations(
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
            logger.exception("Analysis payload validation failed for analysis=%s", analysis.id)
            raise ReportDataValidationError(
                "Failed to validate analysis payload"
            ) from exc

    def _normalise_insights(self, insights: dict[str, Any]) -> dict[str, Any]:
        pain_points = insights.get("pain_points") or []
        for item in pain_points:
            sentiment = float(item.get("sentiment_score", 0.0))
            if not item.get("severity"):
                item["severity"] = self._classify_severity(sentiment)
            item.setdefault("example_posts", [])
            item.setdefault("user_examples", [])

        insights.setdefault("pain_points", pain_points)
        insights.setdefault("competitors", insights.get("competitors") or [])
        insights.setdefault("opportunities", insights.get("opportunities") or [])
        insights.setdefault("action_items", insights.get("action_items") or [])
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
        if "analysis_duration" in migrated_sources and migrated_sources.get(
            "analysis_duration_seconds"
        ) is None:
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
            comp.mentions for comp in competitors if str(comp.sentiment).lower() == "positive"
        )
        negative_mentions = sum(
            item.frequency for item in pain_points if item.sentiment_score < -0.05
        ) + sum(
            comp.mentions for comp in competitors if str(comp.sentiment).lower() == "negative"
        )
        neutral_mentions = max(
            0,
            analysis.sources.posts_analyzed
            - positive_mentions
            - negative_mentions,
        )

        total_mentions = (
            analysis.sources.posts_analyzed
            or positive_mentions
            + negative_mentions
            + neutral_mentions
        )

        return ReportStats(
            total_mentions=max(total_mentions, 0),
            positive_mentions=max(positive_mentions, 0),
            negative_mentions=max(negative_mentions, 0),
            neutral_mentions=max(neutral_mentions, 0),
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
                select(CommunityCache.member_count)
                .where(CommunityCache.community_name == community_name)
            )
            member_count = result.scalar_one_or_none()

            if member_count is not None and member_count > 0:
                logger.debug(f"Using DB member count for {community_name}: {member_count:,}")
                return member_count
        except Exception as e:
            logger.warning(f"Failed to fetch member count from DB for {community_name}: {e}")

        # Fallback to config
        config_count = self._config.community_members.get(community_name.lower())
        if config_count:
            logger.debug(f"Using config member count for {community_name}: {config_count:,}")
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
        sentiment = SentimentBreakdown(
            positive=int(round(stats.positive_mentions / total * 100)),
            negative=int(round(stats.negative_mentions / total * 100)),
            neutral=int(round(stats.neutral_mentions / total * 100)),
        )

        # Build top communities with member counts from DB
        top_communities = []
        for detail in sorted(
            communities_detail,
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

        return ReportOverview(sentiment=sentiment, top_communities=top_communities)

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
            analysis_version=self._format_analysis_version(
                analysis.analysis_version
            ),
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
