from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any

from app.schemas.hotpost import (
    Hotpost,
    HotpostComment,
    HotpostDebugInfo,
    PainPoint,
)
from app.services.hotpost.evidence_focus import is_noise_comment
from app.services.hotpost.keywords import HotpostLexicon
from app.services.hotpost.result_meta import (
    HotpostLLMReportResult,
    HotpostSummaryResult,
    collect_degraded_reasons,
    resolve_hotpost_response_status,
)
from app.services.hotpost.rules import normalize_text

MIGRATION_NAME_STOPWORDS = {
    "the",
    "that",
    "this",
    "them",
    "they",
    "their",
    "there",
    "time",
    "times",
    "thing",
    "things",
    "something",
    "anything",
    "nothing",
    "someone",
    "somebody",
    "everybody",
    "everyone",
    "people",
    "others",
    "other",
    "another",
    "app",
    "apps",
    "tool",
    "tools",
}
COMPETITOR_NAME_STOPWORDS = MIGRATION_NAME_STOPWORDS | {
    "sales",
    "sale",
    "organic",
    "traffic",
    "conversion",
    "conversions",
    "purchase",
    "purchases",
    "buyer",
    "buyers",
    "content",
    "views",
    "reach",
    "ads",
    "advertising",
}


@dataclass(slots=True)
class HotpostResponseBundleInput:
    query_id: str
    query: str
    mode: str
    top_posts: list[Hotpost]
    all_comments: list[HotpostComment]
    notes: list[str]
    resolution_source: str
    resolution_reason:Optional[ str]
    search_query: str
    query_parts: list[str]
    keywords: list[str]
    time_filter: str
    sort: str
    subreddits:Optional[ list[str]]
    raw_posts: int
    filtered_posts: int
    relevance_filtered: int
    summary_result: HotpostSummaryResult
    report_result: HotpostLLMReportResult
    sentiment_overview: dict[str, float]
    confidence: str
    lexicon: HotpostLexicon
    query_intent:Optional[ str] = None
    query_family:Optional[ str] = None
    primary_friction:Optional[ str] = None
    secondary_frictions: list[str] = field(default_factory=list)
    retrieval_hypotheses: list[str] = field(default_factory=list)
    expanded_terms: list[str] = field(default_factory=list)
    negative_terms: list[str] = field(default_factory=list)
    forbidden_narrowing_terms: list[str] = field(default_factory=list)
    candidate_subreddits: list[str] = field(default_factory=list)
    positive_intent_terms: list[str] = field(default_factory=list)
    forbidden_context_terms: list[str] = field(default_factory=list)
    domain_terms: list[str] = field(default_factory=list)
    search_strategy:Optional[ str] = None
    me_too_count: int = 0
    pain_points:Optional[ list[PainPoint]] = None
    opportunities:Optional[ list[dict[str, Any]]] = None
    rant_intensity:Optional[ dict[str, float]] = None
    need_urgency:Optional[ dict[str, float]] = None
    categories: list[str] = field(default_factory=list)
    relevant_posts: int = 0
    lane_yield: dict[str, int] = field(default_factory=dict)
    comment_dive_count: int = 0


def resolve_hotpost_response(
    *,
    resolution_reason:Optional[ str],
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
    resolution_reason:Optional[ str],
    query_intent:Optional[ str],
    query_family:Optional[ str],
    primary_friction:Optional[ str],
    secondary_frictions: list[str],
    search_query: str,
    query_parts: list[str],
    retrieval_hypotheses: list[str],
    keywords: list[str],
    expanded_terms: list[str],
    negative_terms: list[str],
    forbidden_narrowing_terms: list[str],
    candidate_subreddits: list[str],
    positive_intent_terms: list[str],
    forbidden_context_terms: list[str],
    domain_terms: list[str],
    search_strategy:Optional[ str],
    time_filter: str,
    sort: str,
    subreddits:Optional[ list[str]],
    raw_posts: int,
    filtered_posts: int,
    relevance_filtered: int,
    relevant_posts: int,
    voice_hits: int,
    summary_result: HotpostSummaryResult,
    report_result: HotpostLLMReportResult,
    degraded_reasons: list[str],
    response_source: str,
) -> HotpostDebugInfo:
    return HotpostDebugInfo(
        query_source=resolution_source,
        query_degraded_reason=resolution_reason,
        query_intent=query_intent,
        query_family=query_family,
        primary_friction=primary_friction,
        secondary_frictions=secondary_frictions,
        search_query=search_query,
        query_parts=query_parts,
        retrieval_hypotheses=retrieval_hypotheses,
        keywords=keywords,
        expanded_terms=expanded_terms,
        negative_terms=negative_terms,
        forbidden_narrowing_terms=forbidden_narrowing_terms,
        candidate_subreddits=candidate_subreddits,
        positive_intent_terms=positive_intent_terms,
        forbidden_context_terms=forbidden_context_terms,
        domain_terms=domain_terms,
        search_strategy=search_strategy,
        time_filter=time_filter,
        sort=sort,
        selected_subreddits=subreddits or [],
        subreddits=subreddits or [],
        candidate_count=filtered_posts or raw_posts,
        raw_posts=raw_posts,
        filtered_posts=filtered_posts,
        relevance_filtered=relevance_filtered,
        relevant_posts=relevant_posts,
        voice_hits=voice_hits,
        response_source=response_source,
        summary_source=summary_result.source,
        summary_degraded_reason=summary_result.degraded_reason,
        report_source=report_result.source,
        report_degraded_reason=report_result.degraded_reason,
        degraded_reasons=degraded_reasons,
    )


def normalize_migration_destination_name(name: str) -> str:
    cleaned = " ".join(name.split())
    if not cleaned:
        return ""
    normalized = normalize_text(cleaned)
    if not normalized:
        return ""
    pieces = [part for part in cleaned.replace("/", " ").replace("-", " ").split() if part]
    if len(pieces) >= 2:
        last = normalize_text(pieces[-1])
        if last in MIGRATION_NAME_STOPWORDS:
            pieces = pieces[:-1]
    normalized_name = " ".join(pieces).strip()
    if normalize_text(normalized_name) in MIGRATION_NAME_STOPWORDS:
        return ""
    return normalized_name


def stable_migration_destinations(competitors: list[object]) -> list[dict[str, object]]:
    destinations: list[dict[str, object]] = []
    seen_names: set[str] = set()
    for item in competitors[:5]:
        if not isinstance(item, dict):
            continue
        name = normalize_migration_destination_name(str(item.get("name") or ""))
        key = normalize_text(name)
        if not name or not key or key in seen_names:
            continue
        mentions = int(item.get("mentions") or 0)
        if mentions < 2:
            continue
        seen_names.add(key)
        destinations.append({"name": name, "mentions": mentions})
    return destinations


def sanitize_competitor_mentions(
    competitors: list[dict[str, Any]],
    *,
    blocked_terms: set[str],
) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    normalized_blocked = {normalize_text(term) for term in blocked_terms if normalize_text(term)}
    for item in competitors:
        name = " ".join(str(item.get("name") or "").split())
        key = normalize_text(name)
        mentions = int(item.get("mentions") or 0)
        if not name or not key or mentions < 2 or key in seen_names or key in normalized_blocked:
            continue
        if key in MIGRATION_NAME_STOPWORDS or any(part in normalized_blocked or part in MIGRATION_NAME_STOPWORDS for part in key.split()):
            continue
        seen_names.add(key)
        clone = dict(item)
        clone["name"] = name
        cleaned.append(clone)
    return cleaned


def select_key_comments(comments: list[HotpostComment], *, limit: int) -> list[HotpostComment]:
    selected: list[HotpostComment] = []
    for comment in comments:
        body = (comment.body or "").strip()
        if not body or is_noise_comment(comment, min_chars=24):
            continue
        selected.append(comment)
        if len(selected) >= limit:
            break
    return selected


def get_payload_value(item: Any, field: str) -> Any:
    if isinstance(item, dict):
        return item.get(field)
    return getattr(item, field, None)


def set_payload_value(item: Any, field: str, value: Any) -> None:
    if isinstance(item, dict):
        item[field] = value
        return
    if hasattr(item, field):
        setattr(item, field, value)
