from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any, Awaitable, Callable, Mapping, Sequence

from app.core.config import Settings
from app.services.analysis.analysis_audit_summary import build_analysis_audit_summary
from app.services.analysis.analysis_artifacts import apply_report_tier, build_sources_payload
from app.services.analysis.analysis_rendering import (
    AnalysisReportRenderBundle,
    render_analysis_reports,
)
from app.services.analysis.insights_enrichment import summarize_trend_series
from app.services.analysis.topic_profiles import TopicProfile
from app.services.facts_v2.quality import quality_check_facts_v2


@dataclass(frozen=True)
class QualityGateArtifacts:
    insights: dict[str, Any]
    action_reports: list[dict[str, Any]]
    facts_v2_quality: dict[str, Any]
    report_tier: str


@dataclass(frozen=True)
class FinalizedAnalysisOutputs:
    insights: dict[str, Any]
    sources: dict[str, Any]
    report_html: str
    confidence_score: float


def calculate_confidence_score(
    *,
    cache_hit_rate: float,
    posts_analyzed: int,
    communities_found: int,
    pain_points_count: int,
    competitors_count: int,
    opportunities_count: int,
) -> float:
    cache_score = min(cache_hit_rate / 0.9, 1.0) * 0.4
    posts_score = min(posts_analyzed / 100.0, 1.0) * 0.15
    communities_score = min(communities_found / 10.0, 1.0) * 0.15
    pain_points_score = min(pain_points_count / 10.0, 1.0) * 0.1
    competitors_score = min(competitors_count / 5.0, 1.0) * 0.1
    opportunities_score = min(opportunities_count / 5.0, 1.0) * 0.1
    total_score = (
        cache_score
        + posts_score
        + communities_score
        + pain_points_score
        + competitors_score
        + opportunities_score
    )
    return round(min(max(total_score, 0.0), 1.0), 2)


def apply_quality_gate_to_insights(
    *,
    facts_v2_package: Mapping[str, Any],
    topic_profile:Optional[ TopicProfile],
    analysis_blocked_reason:Optional[ str],
    deduped_posts_count: int,
    min_posts: int,
    lookback_days: int,
    insights: Mapping[str, Any],
) -> QualityGateArtifacts:
    quality = quality_check_facts_v2(
        facts_v2_package,
        profile=topic_profile,
        skip_topic_check=topic_profile is None,
    )
    report_tier = quality.tier
    facts_v2_quality: dict[str, Any] = {
        "passed": bool(quality.passed),
        "tier": quality.tier,
        "flags": list(quality.flags),
        "metrics": dict(quality.metrics),
    }
    if analysis_blocked_reason == "insufficient_samples" and report_tier != "X_blocked":
        report_tier = "C_scouting"
        facts_v2_quality["tier"] = "C_scouting"
        facts_v2_quality["passed"] = True
        flags = set(str(x) for x in (facts_v2_quality.get("flags") or []))
        flags.add("insufficient_samples")
        facts_v2_quality["flags"] = sorted(flags)
        metrics = facts_v2_quality.get("metrics")
        if isinstance(metrics, dict):
            metrics.setdefault("filtered_posts", int(deduped_posts_count))
            metrics.setdefault("min_required_posts", int(min_posts))
            metrics.setdefault("lookback_days", int(lookback_days))

    tiered_insights, action_reports = apply_report_tier(
        insights=dict(insights),
        report_tier=report_tier,
    )
    return QualityGateArtifacts(
        insights=tiered_insights,
        action_reports=action_reports,
        facts_v2_quality=facts_v2_quality,
        report_tier=report_tier,
    )


def apply_trend_summary_if_needed(
    *,
    insights: Mapping[str, Any],
    report_tier: str,
    facts_v2_quality:Optional[ Mapping[str, Any]],
    trend_series:Optional[ Sequence[Mapping[str, Any]]],
    trend_degraded: bool,
    trend_sources:Optional[ Sequence[str]],
) -> tuple[dict[str, Any], bool, list[str]]:
    next_insights = dict(insights)
    next_trend_degraded = bool(trend_degraded)
    next_trend_sources = list(trend_sources or [])

    coverage_tier = (
        facts_v2_quality.get("metrics", {}).get("coverage_tier")
        if isinstance(facts_v2_quality, Mapping)
        else None
    )
    if coverage_tier and coverage_tier != "full":
        next_trend_degraded = True
        coverage_reason = f"coverage_{coverage_tier}"
        if coverage_reason not in next_trend_sources:
            next_trend_sources.append(coverage_reason)

    if report_tier not in {"C_scouting", "X_blocked"}:
        next_insights["trend_summary"] = summarize_trend_series(
            trend_series,
            degraded=next_trend_degraded,
            sources=next_trend_sources or None,
        )

    return next_insights, next_trend_degraded, next_trend_sources


async def finalize_analysis_outputs(
    *,
    task: Any,
    collected: Sequence[Any],
    insights: Mapping[str, Any],
    report_tier: str,
    facts_v2_quality:Optional[ Mapping[str, Any]],
    settings: Settings,
    facts_slice: Mapping[str, Any],
    data_lineage: Mapping[str, Any],
    posts_analyzed: int,
    comments_analyzed: int,
    posts_db_current: int,
    comments_db_total: int,
    comments_db_eligible: int,
    comments_pipeline_status: str,
    lookback_days: int,
    cache_hit_rate: float,
    ps_ratio_value: float,
    pain_counts_by_community: Mapping[str, Any],
    keywords: Sequence[str],
    fetch_keywords: Sequence[str],
    processing_seconds: int,
    hybrid_posts_count: int,
    hybrid_retrieval_status:Optional[ str],
    hybrid_retrieval_reason:Optional[ str],
    hybrid_retrieval_query:Optional[ str],
    api_call_count:Optional[ int],
    api_failure_details: Sequence[dict[str, str]],
    stale_cache_subreddits: Sequence[str],
    stale_cache_fallback_subreddits: Sequence[str],
    product_description: str,
    mode: str,
    audit_level: str,
    topic_profile_id:Optional[ str],
    topic_profile_payload:Optional[ Mapping[str, Any]],
    communities_detail: Sequence[Mapping[str, Any]],
    duplicate_summary: Mapping[str, Any],
    dedup_stats: Mapping[str, Any],
    post_score_stats: Mapping[str, Any],
    noise_pool_stats: Mapping[str, Any],
    seed_source: str,
    data_source_label: str,
    coverage_summary: Mapping[str, Any],
    facts_diagnostics:Optional[ Mapping[str, Any]],
    data_readiness:Optional[ Mapping[str, Any]],
    all_remediation_actions:Optional[ Sequence[Mapping[str, Any]]],
    facts_v2_package: Mapping[str, Any],
    knowledge_graph: Mapping[str, Any],
    analysis_blocked_reason:Optional[ str],
    trend_series:Optional[ Sequence[Mapping[str, Any]]],
    build_collection_warnings_fn: Callable[[Sequence[str], Sequence[str], Sequence[dict[str, str]]], list[str]],
    check_trend_views_freshness_fn: Callable[[], Awaitable[tuple[bool, list[str]]]],
    render_analysis_reports_fn: Callable[..., Awaitable[AnalysisReportRenderBundle]] = render_analysis_reports,
) -> FinalizedAnalysisOutputs:
    collection_warnings = build_collection_warnings_fn(
        stale_cache_subreddits,
        stale_cache_fallback_subreddits,
        api_failure_details,
    )
    trend_degraded, trend_sources = await check_trend_views_freshness_fn()
    next_insights, next_trend_degraded, next_trend_sources = apply_trend_summary_if_needed(
        insights=insights,
        report_tier=report_tier,
        facts_v2_quality=facts_v2_quality,
        trend_series=trend_series,
        trend_degraded=trend_degraded,
        trend_sources=trend_sources,
    )

    sources = build_sources_payload(
        communities=[entry.profile.name for entry in collected],
        posts_analyzed=posts_analyzed,
        comments_analyzed=comments_analyzed,
        data_lineage=data_lineage,
        counts_db={
            "posts_current": int(posts_db_current),
            "comments_total": int(comments_db_total),
            "comments_eligible": int(comments_db_eligible),
        },
        comments_pipeline_status=comments_pipeline_status,
        lookback_days=int(lookback_days),
        cache_hit_rate=float(cache_hit_rate),
        ps_ratio=ps_ratio_value,
        pain_counts_by_community=pain_counts_by_community,
        keywords=keywords,
        fetch_keywords=fetch_keywords,
        analysis_duration_seconds=processing_seconds,
        hybrid_posts_used=hybrid_posts_count,
        hybrid_retrieval_status=hybrid_retrieval_status,
        hybrid_retrieval_reason=hybrid_retrieval_reason,
        hybrid_retrieval_query=hybrid_retrieval_query,
        reddit_api_calls=api_call_count,
        reddit_api_failures=api_failure_details,
        stale_cache_subreddits=stale_cache_subreddits,
        stale_cache_fallback_subreddits=stale_cache_fallback_subreddits,
        collection_warnings=collection_warnings,
        product_description=product_description,
        mode=mode,
        audit_level=audit_level,
        topic_profile_id=topic_profile_id,
        topic_profile=topic_profile_payload,
        communities_detail=communities_detail,
        duplicates_summary=duplicate_summary,
        facts_v2_quality=facts_v2_quality,
        report_tier=report_tier,
        dedup_stats=dedup_stats,
        post_score_stats=post_score_stats,
        noise_pool_stats=noise_pool_stats,
        seed_source=seed_source,
        data_source=data_source_label,
        coverage_status=coverage_summary,
        trend_degraded=bool(next_trend_degraded),
        trend_source=next_trend_sources or None,
        analysis_diagnostics=facts_diagnostics if facts_diagnostics else None,
        data_readiness=data_readiness,
        remediation_actions=all_remediation_actions or None,
        facts_v2_package=facts_v2_package,
        facts_slice=facts_slice,
        knowledge_graph=knowledge_graph,
        analysis_blocked=analysis_blocked_reason,
    )

    flags: list[str] = []
    suggestion = ""
    if report_tier == "X_blocked":
        flags = (
            list((facts_v2_quality or {}).get("flags", []))
            if isinstance(facts_v2_quality, Mapping)
            else []
        )
        if topic_profile_id:
            suggestion = "换一个更准的 `topic_profile_id`，或扩充样本（更多社区/更长时间窗/更明确关键词）。"
        else:
            suggestion = "先扩充样本（更多社区/更长时间窗/更明确关键词），再看是否需要建立 topic_profile。"

    render_bundle = await render_analysis_reports_fn(
        task=task,
        communities=collected,
        insights=next_insights,
        sources=sources,
        facts_slice=facts_slice,
        report_tier=report_tier,
        settings=settings,
        blocked_flags=flags,
        blocked_suggestion=suggestion,
    )
    sources["report_structured"] = (
        render_bundle.structured_render.report if render_bundle.structured_render.report else sources.get("report_structured")
    )
    sources["structured_llm_status"] = render_bundle.structured_render.status
    sources["structured_llm_reason"] = render_bundle.structured_render.reason
    sources["llm_used"] = bool(render_bundle.structured_render.model)
    sources["llm_model"] = render_bundle.structured_render.model
    sources["llm_rounds"] = render_bundle.structured_render.rounds
    sources["analysis_audit"] = build_analysis_audit_summary(
        sources=sources,
        report_tier=report_tier,
        analysis_blocked=sources.get("analysis_blocked")
        if isinstance(sources.get("analysis_blocked"), str)
        else analysis_blocked_reason,
    )

    cache_hit_rate_value = sources["cache_hit_rate"]
    posts_analyzed_value = sources["posts_analyzed"]
    communities_value = sources["communities"]
    pain_points_value = next_insights["pain_points"]
    competitors_value = next_insights["competitors"]
    opportunities_value = next_insights["opportunities"]

    confidence_score = calculate_confidence_score(
        cache_hit_rate=float(cache_hit_rate_value)
        if isinstance(cache_hit_rate_value, (int, float))
        else 0.0,
        posts_analyzed=int(posts_analyzed_value)
        if isinstance(posts_analyzed_value, int)
        else 0,
        communities_found=len(communities_value) if isinstance(communities_value, list) else 0,
        pain_points_count=len(pain_points_value) if isinstance(pain_points_value, list) else 0,
        competitors_count=len(competitors_value) if isinstance(competitors_value, list) else 0,
        opportunities_count=len(opportunities_value) if isinstance(opportunities_value, list) else 0,
    )

    return FinalizedAnalysisOutputs(
        insights=next_insights,
        sources=sources,
        report_html=render_bundle.report_html,
        confidence_score=confidence_score,
    )
