from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Optional, Any


def build_facts_v2_package(
    *,
    topic_label: str,
    topic_profile_id:Optional[ str],
    product_description: str,
    data_lineage: Mapping[str, Any],
    high_value_pains: Sequence[Mapping[str, Any]],
    brand_pain: Sequence[Mapping[str, Any]],
    solutions: Sequence[Mapping[str, Any]],
    opportunities: Sequence[Mapping[str, Any]],
    competitors: Sequence[Mapping[str, Any]],
    ps_ratio:Optional[ float],
    sample_posts_db: Sequence[Mapping[str, Any]],
    sample_comments_db: Sequence[Mapping[str, Any]],
    diagnostics:Optional[ Mapping[str, Any]] = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "2.0",
        "meta": {
            "topic": topic_label,
            "topic_profile_id": topic_profile_id,
            "product_description": product_description,
        },
        "data_lineage": dict(data_lineage),
        "aggregates": {},
        "business_signals": {
            "high_value_pains": list(high_value_pains),
            "brand_pain": list(brand_pain),
            "solutions": list(solutions),
            "buying_opportunities": list(opportunities),
            "competitor_insights": list(competitors),
            "ps_ratio": round(ps_ratio, 2) if ps_ratio is not None else None,
        },
        "sample_posts_db": list(sample_posts_db),
        "sample_comments_db": list(sample_comments_db),
    }
    if diagnostics:
        payload["diagnostics"] = dict(diagnostics)
    return payload


def attach_aggregates(
    facts_v2_package: dict[str, Any],
    *,
    aggregates: Mapping[str, Any],
) -> dict[str, Any]:
    enriched = dict(facts_v2_package)
    enriched["aggregates"] = dict(aggregates)
    return enriched


def apply_report_tier(
    *,
    insights: Mapping[str, Any],
    report_tier:Optional[ str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    adjusted = dict(insights)
    action_reports = list(adjusted.get("action_items") or [])
    if report_tier == "B_trimmed":
        adjusted["pain_points"] = list(adjusted.get("pain_points") or [])[:2]
        adjusted["opportunities"] = list(adjusted.get("opportunities") or [])[:2]
        adjusted["action_items"] = action_reports[:1]
        action_reports = list(adjusted.get("action_items") or [])
    elif report_tier in {"C_scouting", "X_blocked"}:
        adjusted = {
            "pain_points": [],
            "competitors": [],
            "opportunities": [],
            "action_items": [],
        }
        action_reports = []
    return adjusted, action_reports


def build_sources_payload(
    *,
    communities: Sequence[str],
    posts_analyzed: int,
    comments_analyzed: int,
    data_lineage: Mapping[str, Any],
    counts_db: Mapping[str, Any],
    comments_pipeline_status: str,
    lookback_days: int,
    cache_hit_rate: float,
    ps_ratio:Optional[ float],
    pain_counts_by_community: Mapping[str, int],
    keywords: Sequence[str],
    fetch_keywords: Sequence[str],
    analysis_duration_seconds: int,
    hybrid_posts_used: int,
    hybrid_retrieval_status:Optional[ str],
    hybrid_retrieval_reason:Optional[ str],
    hybrid_retrieval_query:Optional[ str],
    reddit_api_calls: int,
    reddit_api_failures: Sequence[Mapping[str, Any]],
    stale_cache_subreddits: Sequence[str],
    stale_cache_fallback_subreddits: Sequence[str],
    collection_warnings: Sequence[Mapping[str, Any]],
    product_description: str,
    mode: str,
    audit_level: str,
    topic_profile_id:Optional[ str],
    topic_profile:Optional[ Mapping[str, Any]],
    communities_detail: Sequence[Mapping[str, Any]],
    duplicates_summary: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    facts_v2_quality:Optional[ Mapping[str, Any]],
    report_tier:Optional[ str],
    dedup_stats: Mapping[str, Any],
    post_score_stats: Mapping[str, Any],
    noise_pool_stats: Mapping[str, Any],
    seed_source: str,
    data_source: str,
    coverage_status:Optional[ Mapping[str, Any]],
    trend_degraded: bool,
    trend_source:Optional[ Sequence[str]],
    analysis_diagnostics:Optional[ Mapping[str, Any]] = None,
    data_readiness:Optional[ Mapping[str, Any]] = None,
    remediation_actions:Optional[ Sequence[Mapping[str, Any]]] = None,
    facts_v2_package:Optional[ Mapping[str, Any]] = None,
    facts_slice:Optional[ Mapping[str, Any]] = None,
    knowledge_graph:Optional[ Mapping[str, Any]] = None,
    analysis_blocked:Optional[ str] = None,
) -> dict[str, Any]:
    normalized_duplicates_summary: list[dict[str, Any]]
    if isinstance(duplicates_summary, Mapping):
        normalized_duplicates_summary = [dict(duplicates_summary)]
    else:
        normalized_duplicates_summary = [
            dict(item) for item in duplicates_summary if isinstance(item, Mapping)
        ]

    sources: dict[str, Any] = {
        "communities": list(communities),
        "posts_analyzed": posts_analyzed,
        "comments_analyzed": comments_analyzed,
        "data_lineage": dict(data_lineage),
        "counts_analyzed": {"posts": posts_analyzed, "comments": comments_analyzed},
        "counts_db": dict(counts_db),
        "comments_pipeline_status": comments_pipeline_status,
        "lookback_days": lookback_days,
        "cache_hit_rate": round(cache_hit_rate, 2),
        "ps_ratio": round(ps_ratio, 2) if ps_ratio is not None else None,
        "pain_counts_by_community": dict(pain_counts_by_community),
        "keywords": list(keywords),
        "fetch_keywords": list(fetch_keywords),
        "analysis_duration_seconds": analysis_duration_seconds,
        "hybrid_posts_used": hybrid_posts_used,
        "hybrid_retrieval_status": hybrid_retrieval_status,
        "hybrid_retrieval_reason": hybrid_retrieval_reason,
        "hybrid_retrieval_query": hybrid_retrieval_query,
        "reddit_api_calls": reddit_api_calls,
        "reddit_api_failures": list(reddit_api_failures),
        "stale_cache_subreddits": sorted(stale_cache_subreddits),
        "stale_cache_fallback_subreddits": sorted(stale_cache_fallback_subreddits),
        "collection_warnings": list(collection_warnings),
        "product_description": product_description,
        "mode": mode,
        "audit_level": audit_level,
        "topic_profile_id": topic_profile_id,
        "topic_profile": dict(topic_profile) if topic_profile is not None else None,
        "communities_detail": list(communities_detail),
        "duplicates_summary": normalized_duplicates_summary,
        "facts_v2_quality": dict(facts_v2_quality) if facts_v2_quality is not None else None,
        "report_tier": report_tier,
        "dedup_stats": dict(dedup_stats),
        "post_score_stats": dict(post_score_stats),
        "noise_pool_stats": dict(noise_pool_stats),
        "seed_source": seed_source,
        "data_source": data_source,
        "coverage_status": dict(coverage_status) if coverage_status is not None else None,
        "trend_degraded": trend_degraded,
        "trend_source": list(trend_source) if trend_source else None,
    }
    if analysis_diagnostics:
        sources["analysis_diagnostics"] = dict(analysis_diagnostics)
    if data_readiness is not None:
        sources["data_readiness"] = dict(data_readiness)
    if remediation_actions:
        sources["remediation_actions"] = list(remediation_actions)
    if facts_v2_package is not None:
        sources["facts_v2_package"] = dict(facts_v2_package)
    if facts_slice is not None:
        sources["facts_slice"] = dict(facts_slice)
    if knowledge_graph is not None:
        sources["knowledge_graph"] = dict(knowledge_graph)
    if analysis_blocked:
        sources["analysis_blocked"] = analysis_blocked
    if report_tier == "X_blocked":
        sources.setdefault("analysis_blocked", "quality_gate_blocked")
    if report_tier == "C_scouting":
        sources.setdefault("analysis_blocked", "scouting_brief")
    return sources


__all__ = [
    "apply_report_tier",
    "attach_aggregates",
    "build_facts_v2_package",
    "build_sources_payload",
]
