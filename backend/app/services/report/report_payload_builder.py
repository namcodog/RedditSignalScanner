from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping, Sequence

from app.schemas.analysis import (
    AnalysisRead,
    CommunitySourceDetail,
    EntityLeaderboardItem,
    InsightsPayload,
    OpportunityReportOut,
    SourcesPayload,
)
from app.schemas.report_payload import (
    FallbackQuality,
    MarketHealth,
    ReportContent,
    ReportExecutiveSummary,
    ReportMetadata,
    ReportOverview,
    ReportPayload,
    ReportStats,
    SentimentBreakdown,
    TopCommunity,
)
from app.services.report.render_bundle import ReportRenderBundle
from app.utils.url import normalize_reddit_url


@dataclass(slots=True, frozen=True)
class ReportPayloadBuildInput:
    task: Any
    analysis: AnalysisRead
    generated_at: Any
    action_items: list[OpportunityReportOut]
    render_bundle: ReportRenderBundle


async def build_report_payload(
    *,
    build_input: ReportPayloadBuildInput,
    fetch_member_count: Callable[[str], Awaitable[int]],
) -> ReportPayload:
    _apply_phrase_mapping(
        action_items=build_input.action_items,
        pain_points=build_input.analysis.insights.pain_points,
        opportunities=build_input.analysis.insights.opportunities,
    )
    _normalize_example_post_urls(build_input.analysis.insights.pain_points)

    stats = build_report_stats(build_input.analysis)
    overview = await build_report_overview(
        build_input.analysis.sources.communities_detail or [],
        stats,
        fetch_member_count=fetch_member_count,
    )
    summary = build_report_summary(
        build_input.analysis.insights,
        build_input.analysis.sources,
    )
    market_health = build_market_health(
        build_input.analysis.insights,
        build_input.analysis.sources,
    )
    entity_leaderboard = build_entity_leaderboard(build_input.analysis.insights)
    metadata = build_report_metadata(
        task=build_input.task,
        analysis=build_input.analysis,
        generated_at=build_input.generated_at,
        stats=stats,
    )
    metadata.market_enhancements = build_input.render_bundle.market_enhancements
    metadata.llm_used = metadata.llm_used or build_input.render_bundle.llm_used
    _apply_recovery_markers(
        overview=overview,
        sources=build_input.analysis.sources,
        metadata=metadata,
        action_items=build_input.action_items,
    )

    return ReportPayload(
        task_id=build_input.task.id,
        status=build_input.task.status,
        generated_at=build_input.generated_at,
        product_description=build_input.analysis.sources.product_description
        or build_input.task.product_description,
        report_structured=build_input.analysis.sources.report_structured,
        report=ReportContent(
            executive_summary=summary,
            pain_points=build_input.analysis.insights.pain_points,
            pain_clusters=build_input.analysis.insights.pain_clusters,
            competitors=build_input.analysis.insights.competitors,
            opportunities=build_input.analysis.insights.opportunities,
            action_items=build_input.action_items,
            purchase_drivers=build_input.analysis.insights.top_drivers,
            market_health=market_health,
            entity_summary=build_input.analysis.insights.entity_summary,
            entity_leaderboard=entity_leaderboard,
            competitor_layers_summary=build_input.analysis.insights.competitor_layers_summary,
            channel_breakdown=build_input.analysis.insights.channel_breakdown,
        ),
        metadata=metadata,
        overview=overview,
        stats=stats,
        sources=build_input.analysis.sources,
        report_html=build_input.render_bundle.report_html
        or (
            build_input.task.analysis.report.html_content
            if getattr(build_input.task, "analysis", None) is not None
            else None
        ),
        metrics_summary=build_input.render_bundle.metrics_summary,
    )


def build_report_stats(analysis: AnalysisRead) -> ReportStats:
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
    neutral_candidates = analysis.sources.posts_analyzed - positive_mentions - negative_mentions
    neutral_mentions = max(0, neutral_candidates)

    pos = max(int(positive_mentions), 0)
    neg = max(int(negative_mentions), 0)
    neu = max(int(neutral_mentions), 0)
    total = pos + neg + neu

    return ReportStats(
        total_mentions=total,
        positive_mentions=pos,
        negative_mentions=neg,
        neutral_mentions=neu,
    )


async def build_report_overview(
    communities_detail: list[CommunitySourceDetail],
    stats: ReportStats,
    *,
    fetch_member_count: Callable[[str], Awaitable[int]],
) -> ReportOverview:
    total = max(stats.total_mentions, 1)
    positive_pct = stats.positive_mentions / total * 100
    negative_pct = stats.negative_mentions / total * 100
    neutral_pct = stats.neutral_mentions / total * 100

    positive = max(0, min(100, int(round(positive_pct))))
    negative = max(0, min(100, int(round(negative_pct))))
    neutral = max(0, min(100, int(round(neutral_pct))))

    total_pct = positive + negative + neutral
    if total_pct > 100:
        if positive >= negative and positive >= neutral:
            positive -= total_pct - 100
        elif negative >= neutral:
            negative -= total_pct - 100
        else:
            neutral -= total_pct - 100

    sentiment = SentimentBreakdown(
        positive=max(0, positive),
        negative=max(0, negative),
        neutral=max(0, neutral),
    )

    filtered_details = communities_detail
    try:
        from app.services.community.blacklist_loader import get_blacklist_config

        blacklist = get_blacklist_config()
        filtered_details = [
            detail
            for detail in communities_detail
            if not blacklist.is_community_blacklisted(detail.name)
        ] or communities_detail
    except Exception:
        filtered_details = communities_detail

    top_communities: list[TopCommunity] = []
    for detail in sorted(
        filtered_details,
        key=lambda item: item.mentions,
        reverse=True,
    )[:5]:
        member_count = await fetch_member_count(detail.name)
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

    total_communities = len(communities_detail)
    top_n = len(top_communities)
    seed_source = None
    try:
        if any("discovered" in (detail.categories or []) for detail in communities_detail):
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


def build_report_summary(
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


def build_market_health(
    insights: InsightsPayload,
    sources: SourcesPayload,
) -> MarketHealth | None:
    saturation_scores: list[float] = []
    for item in insights.market_saturation or []:
        try:
            score = float(getattr(item, "overall_saturation", None) or 0.0)
        except Exception:
            continue
        saturation_scores.append(max(0.0, min(1.0, score)))

    saturation_score = None
    if saturation_scores:
        saturation_score = sum(saturation_scores) / max(1, len(saturation_scores))

    saturation_level = None
    if saturation_score is not None:
        if saturation_score >= 0.7:
            saturation_level = "high"
        elif saturation_score <= 0.4:
            saturation_level = "low"
        else:
            saturation_level = "medium"

    ps_ratio_value = None
    try:
        facts_slice = sources.facts_slice or {}
        if isinstance(facts_slice, Mapping):
            for key in ("ps_ratio", "ps_ratio_value", "ps_ratio_mean"):
                raw = facts_slice.get(key)
                if isinstance(raw, (int, float)):
                    ps_ratio_value = float(raw)
                    break
        if ps_ratio_value is None:
            raw = getattr(sources, "ps_ratio", None)
            if isinstance(raw, (int, float)):
                ps_ratio_value = float(raw)
    except Exception:
        ps_ratio_value = None

    ps_ratio_assessment = None
    if ps_ratio_value is not None:
        if 0.8 <= ps_ratio_value <= 1.2:
            ps_ratio_assessment = "healthy"
        else:
            ps_ratio_assessment = "imbalanced"

    if saturation_score is None and ps_ratio_value is None:
        return None

    return MarketHealth(
        saturation_level=saturation_level or "unknown",
        saturation_score=saturation_score,
        ps_ratio=ps_ratio_value,
        ps_ratio_assessment=ps_ratio_assessment
        or ("unknown" if ps_ratio_value is None else None),
    )


def build_report_metadata(
    *,
    task: Any,
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

    llm_used = analysis.sources.llm_used
    llm_model = analysis.sources.llm_model
    llm_rounds = analysis.sources.llm_rounds
    if not llm_model:
        try:
            from app.core.config import settings as app_settings

            llm_model = getattr(app_settings, "llm_model_name", "local-extractive")
        except Exception:
            llm_model = "local-extractive"
    if llm_rounds is None:
        if llm_used is None:
            llm_rounds = None
        else:
            llm_rounds = 2 if llm_used else 0

    lexver: str | None = None
    try:
        import json as _json
        import os as _os

        env_ver = _os.getenv("SEMANTIC_LEXICON_VERSION")
        if env_ver and env_ver.strip():
            lexver = env_ver.strip()
        else:
            lex_path = Path(
                _os.getenv(
                    "SEMANTIC_LEXICON_PATH",
                    "backend/config/semantic_sets/crossborder_v2.1.yml",
                )
            )
            if lex_path.exists():
                text = lex_path.read_text(encoding="utf-8")
                try:
                    payload = _json.loads(text)
                    version = payload.get("version") if isinstance(payload, dict) else None
                    if isinstance(version, str) and version.strip():
                        lexver = version.strip()
                except Exception:
                    stem = lex_path.stem
                    for token in stem.split("_") + stem.split("-"):
                        if token.lower().startswith("v") and any(ch.isdigit() for ch in token):
                            lexver = token
                            break
    except Exception:
        lexver = None

    return ReportMetadata(
        analysis_version=_format_analysis_version(analysis.analysis_version),
        confidence_score=float(analysis.confidence_score or 0.0),
        processing_time_seconds=float(processing_seconds or 0.0),
        cache_hit_rate=float(analysis.sources.cache_hit_rate or 0.0),
        total_mentions=stats.total_mentions,
        recovery_applied=analysis.sources.recovery_strategy,
        fallback_quality=fallback_quality,
        llm_used=llm_used,
        llm_model=llm_model,
        llm_rounds=llm_rounds,
        lexicon_version=lexver,
    )


def build_entity_leaderboard(insights: InsightsPayload) -> list[EntityLeaderboardItem]:
    entity_leaderboard: list[EntityLeaderboardItem] = []
    try:
        entity_summary = insights.entity_summary
        for category in (
            "brands",
            "features",
            "pain_points",
            "channels",
            "logistics",
            "risks",
        ):
            rows = getattr(entity_summary, category, [])
            for row in rows or []:
                name = getattr(row, "name", None)
                mentions = getattr(row, "mentions", 0) or 0
                if isinstance(name, str):
                    entity_leaderboard.append(
                        EntityLeaderboardItem(
                            name=name,
                            category=category,
                            mentions=max(0, int(mentions)),
                        )
                    )
        entity_leaderboard.sort(key=lambda item: item.mentions, reverse=True)
        return entity_leaderboard[:20]
    except Exception:
        return []


def _apply_recovery_markers(
    *,
    overview: ReportOverview,
    sources: SourcesPayload,
    metadata: ReportMetadata,
    action_items: Sequence[OpportunityReportOut],
) -> None:
    try:
        pct_sum = (
            overview.sentiment.positive
            + overview.sentiment.negative
            + overview.sentiment.neutral
        )
        recovery_reasons: list[str] = []
        if pct_sum < 98 or pct_sum > 102:
            recovery_reasons.append("stats_inconsistency")
        if any("证据不足(n<2)" in (item.suggested_actions or []) for item in action_items):
            recovery_reasons.append("insufficient_evidence")
        if recovery_reasons:
            existing = (sources.recovery_strategy or "").strip()
            merged = ",".join(filter(None, [existing] + recovery_reasons)).strip(",")
            sources.recovery_strategy = merged or None
            metadata.recovery_applied = merged or None
    except Exception:
        return


def _apply_phrase_mapping(
    *,
    action_items: Sequence[OpportunityReportOut],
    pain_points: Sequence[Any],
    opportunities: Sequence[Any],
) -> None:
    def _normalize_text(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        try:
            import yaml  # type: ignore

            mapping_file = Path("backend/config/phrase_mapping.yml")
            mapping: dict[str, str] = {}
            if mapping_file.exists():
                mapping = yaml.safe_load(mapping_file.read_text(encoding="utf-8")) or {}
            for old, new in mapping.items():
                value = value.replace(old, new)
        except Exception:
            return value
        return value

    for item in action_items:
        try:
            if item.problem_definition:
                item.problem_definition = _normalize_text(item.problem_definition)
            if item.suggested_actions:
                item.suggested_actions = [
                    _normalize_text(action) for action in item.suggested_actions
                ]
        except Exception:
            continue

    for collection in (pain_points, opportunities):
        for obj in collection:
            try:
                if hasattr(obj, "description") and obj.description:
                    obj.description = _normalize_text(obj.description)
            except Exception:
                continue


def _normalize_example_post_urls(pain_points: Sequence[Any]) -> None:
    for pain in pain_points:
        posts = getattr(pain, "example_posts", None) or []
        for post in posts:
            try:
                if isinstance(post, dict):
                    raw_url = post.get("url") or ""
                    raw_permalink = post.get("permalink") or ""
                    post["url"] = normalize_reddit_url(
                        url=str(raw_url or ""),
                        permalink=str(raw_permalink or ""),
                    )
                else:
                    raw_url = getattr(post, "url", None) or ""
                    raw_permalink = getattr(post, "permalink", None) or ""
                    normalized = normalize_reddit_url(
                        url=str(raw_url or ""),
                        permalink=str(raw_permalink or ""),
                    )
                    setattr(post, "url", normalized)
            except Exception:
                continue


def _format_analysis_version(version: Any) -> str:
    try:
        numeric = float(version)
    except (TypeError, ValueError):
        return str(version)
    if numeric.is_integer():
        return f"{numeric:.1f}"
    return str(numeric)


__all__ = [
    "ReportPayloadBuildInput",
    "build_entity_leaderboard",
    "build_market_health",
    "build_report_metadata",
    "build_report_overview",
    "build_report_payload",
    "build_report_stats",
    "build_report_summary",
]
