from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.schemas.hotpost import (
    Hotpost,
    HotpostComment,
    HotpostDebugInfo,
    HotpostSearchResponse,
    PainPoint,
)
from app.services.hotpost.detail_builder import (
    build_top_discovery_posts,
    build_top_rants,
    extract_competitor_mentions,
)
from app.services.hotpost.enrichment import enrich_opportunity_payload, enrich_rant_payload
from app.services.hotpost.keywords import HotpostLexicon
from app.services.hotpost.report_export import export_markdown_report
from app.services.hotpost.report_llm import (
    apply_hotpost_llm_annotations,
    merge_hotpost_llm_report,
)
from app.services.hotpost.result_meta import (
    HotpostLLMReportResult,
    HotpostSummaryResult,
    collect_degraded_reasons,
    resolve_hotpost_response_status,
)
from app.services.hotpost.rules import classify_intent_label, normalize_text


@dataclass(slots=True)
class HotpostResponseBundleInput:
    query_id: str
    query: str
    mode: str
    top_posts: list[Hotpost]
    all_comments: list[HotpostComment]
    notes: list[str]
    resolution_source: str
    resolution_reason: str | None
    search_query: str
    query_parts: list[str]
    keywords: list[str]
    time_filter: str
    sort: str
    subreddits: list[str] | None
    raw_posts: int
    filtered_posts: int
    relevance_filtered: int
    summary_result: HotpostSummaryResult
    report_result: HotpostLLMReportResult
    sentiment_overview: dict[str, float]
    confidence: str
    lexicon: HotpostLexicon
    me_too_count: int = 0
    pain_points: list[PainPoint] | None = None
    opportunities: list[dict[str, Any]] | None = None
    rant_intensity: dict[str, float] | None = None
    need_urgency: dict[str, float] | None = None
    categories: list[str] = field(default_factory=list)


def resolve_hotpost_response(
    *,
    resolution_reason: str | None,
    summary_result: HotpostSummaryResult,
    report_result: HotpostLLMReportResult,
) -> tuple[str, list[str]]:
    degraded_reasons = collect_degraded_reasons(
        resolution_reason,
        summary_result.degraded_reason,
        report_result.degraded_reason if report_result.source != "disabled" else None,
    )
    return resolve_hotpost_response_status(*degraded_reasons), degraded_reasons


def build_hotpost_debug_info(
    *,
    resolution_source: str,
    resolution_reason: str | None,
    search_query: str,
    query_parts: list[str],
    keywords: list[str],
    time_filter: str,
    sort: str,
    subreddits: list[str] | None,
    raw_posts: int,
    filtered_posts: int,
    relevance_filtered: int,
    summary_result: HotpostSummaryResult,
    report_result: HotpostLLMReportResult,
    degraded_reasons: list[str],
    response_source: str,
) -> HotpostDebugInfo:
    return HotpostDebugInfo(
        query_source=resolution_source,
        query_degraded_reason=resolution_reason,
        search_query=search_query,
        query_parts=query_parts,
        keywords=keywords,
        time_filter=time_filter,
        sort=sort,
        subreddits=subreddits or [],
        raw_posts=raw_posts,
        filtered_posts=filtered_posts,
        relevance_filtered=relevance_filtered,
        response_source=response_source,
        summary_source=summary_result.source,
        summary_degraded_reason=summary_result.degraded_reason,
        report_source=report_result.source,
        report_degraded_reason=report_result.degraded_reason,
        llm_report_applied=bool(report_result.report),
        degraded_reasons=degraded_reasons,
    )


def build_hotpost_search_response(bundle: HotpostResponseBundleInput) -> HotpostSearchResponse:
    evidence_count = len(bundle.top_posts)
    community_counts = Counter(post.subreddit for post in bundle.top_posts)
    community_distribution = {
        sub: f"{count / evidence_count * 100:.0f}%" if evidence_count else "0%"
        for sub, count in community_counts.most_common(5)
    }

    status_value, degraded_reasons = resolve_hotpost_response(
        resolution_reason=bundle.resolution_reason,
        summary_result=bundle.summary_result,
        report_result=bundle.report_result,
    )
    debug_info = build_hotpost_debug_info(
        resolution_source=bundle.resolution_source,
        resolution_reason=bundle.resolution_reason,
        search_query=bundle.search_query,
        query_parts=bundle.query_parts,
        keywords=bundle.keywords,
        time_filter=bundle.time_filter,
        sort=bundle.sort,
        subreddits=bundle.subreddits,
        raw_posts=bundle.raw_posts,
        filtered_posts=bundle.filtered_posts,
        relevance_filtered=bundle.relevance_filtered,
        summary_result=bundle.summary_result,
        report_result=bundle.report_result,
        degraded_reasons=degraded_reasons,
        response_source="live",
    )

    response_payload: dict[str, Any] = {
        "query_id": bundle.query_id,
        "query": bundle.query,
        "mode": bundle.mode,
        "search_time": datetime.now(timezone.utc),
        "from_cache": False,
        "status": status_value,
        "summary": bundle.summary_result.text,
        "top_posts": bundle.top_posts,
        "key_comments": sorted(
            bundle.all_comments,
            key=lambda c: c.score or 0,
            reverse=True,
        )[:5],
        "pain_points": bundle.pain_points,
        "opportunities": bundle.opportunities,
        "trending_keywords": None,
        "communities": list(community_counts.keys()),
        "related_queries": [],
        "evidence_count": evidence_count,
        "community_distribution": community_distribution,
        "sentiment_overview": bundle.sentiment_overview,
        "rant_intensity": bundle.rant_intensity,
        "need_urgency": bundle.need_urgency,
        "confidence": bundle.confidence,
        "notes": bundle.notes,
        "debug_info": debug_info,
    }

    response_payload = merge_hotpost_llm_report(response_payload, bundle.report_result.report)
    response_payload = apply_hotpost_llm_annotations(response_payload, bundle.report_result.report)

    opportunity_strength: str | None = None
    if bundle.mode == "rant":
        category_counts = Counter(bundle.categories)
        response_payload = enrich_rant_payload(
            response_payload,
            category_counts=category_counts,
            lexicon=bundle.lexicon,
            fallback_quotes=[p.title for p in bundle.top_posts if p.title][:3],
            evidence_count=evidence_count,
        )
        if not response_payload.get("competitor_mentions"):
            response_payload["competitor_mentions"] = extract_competitor_mentions(
                bundle.top_posts,
                query=bundle.query,
            )

        intent_counts = Counter()
        for post in bundle.top_posts:
            text = normalize_text(f"{post.title} {post.body_preview or ''}")
            intent_counts[classify_intent_label(text, bundle.lexicon)] += 1
        total_intents = sum(intent_counts.values())
        total_mentions = intent_counts.get("already_left", 0) + intent_counts.get("considering", 0)
        percentage = total_mentions / total_intents if total_intents else 0.0
        response_payload["migration_intent"] = {
            "already_left": f"{intent_counts.get('already_left', 0) / total_intents * 100:.0f}%"
            if total_intents
            else "0%",
            "considering": f"{intent_counts.get('considering', 0) / total_intents * 100:.0f}%"
            if total_intents
            else "0%",
            "staying_reluctantly": f"{intent_counts.get('staying_reluctantly', 0) / total_intents * 100:.0f}%"
            if total_intents
            else "0%",
            "total_mentions": total_mentions,
            "percentage": round(percentage, 4),
            "status_distribution": {
                "already_left": intent_counts.get("already_left", 0) / total_intents if total_intents else 0.0,
                "considering": intent_counts.get("considering", 0) / total_intents if total_intents else 0.0,
                "staying": intent_counts.get("staying_reluctantly", 0) / total_intents if total_intents else 0.0,
            },
        }
        response_payload["top_rants"] = build_top_rants(bundle.top_posts)
        migration = response_payload.get("migration_intent") or {}
        destinations: list[dict[str, object]] = []
        competitors = response_payload.get("competitor_mentions") or []
        for comp in competitors:
            if hasattr(comp, "model_dump"):
                comp_data = comp.model_dump()
            elif isinstance(comp, dict):
                comp_data = comp
            else:
                continue
            destinations.append(
                {
                    "name": comp_data.get("name"),
                    "mentions": comp_data.get("mentions"),
                    "sentiment": comp_data.get("sentiment"),
                }
            )
        if destinations:
            migration["destinations"] = destinations
        if not migration.get("key_quote") and bundle.top_posts:
            first_comments = bundle.top_posts[0].top_comments or []
            if first_comments:
                migration["key_quote"] = first_comments[0].body
        response_payload["migration_intent"] = migration

    if bundle.mode == "opportunity":
        opportunity_strength = "weak"
        if evidence_count >= 20 and bundle.me_too_count >= 5:
            opportunity_strength = "strong"
        elif evidence_count >= 10:
            opportunity_strength = "medium"
        response_payload["opportunity_strength"] = opportunity_strength
        response_payload = enrich_opportunity_payload(
            response_payload,
            me_too_count=bundle.me_too_count,
            opportunity_strength=opportunity_strength,
        )
        response_payload["top_discovery_posts"] = build_top_discovery_posts(bundle.top_posts)
        response_payload["opportunity_strength"] = opportunity_strength
        market = response_payload.get("market_opportunity")
        if isinstance(market, dict):
            if opportunity_strength:
                market.setdefault("strength", opportunity_strength)
            response_payload["market_opportunity"] = market

    if evidence_count < 10:
        response_payload["reliability_note"] = f"当前样本量 {evidence_count} 条，样本有限，仅供预览。"
    else:
        response_payload["reliability_note"] = f"基于 {evidence_count} 条证据帖的抽样结果。"

    response_payload["next_steps"] = {
        "deepdive_available": True,
        "deepdive_token": None,
        "suggested_keywords": bundle.keywords[:5],
    }

    enable_markdown = os.getenv("ENABLE_HOTPOST_MARKDOWN_EXPORT", "true").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if enable_markdown:
        response_payload["markdown_report"] = export_markdown_report(response_payload)

    return HotpostSearchResponse(**response_payload)


__all__ = [
    "HotpostResponseBundleInput",
    "build_hotpost_debug_info",
    "build_hotpost_search_response",
    "resolve_hotpost_response",
]
