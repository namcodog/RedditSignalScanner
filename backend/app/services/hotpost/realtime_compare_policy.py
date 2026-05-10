from __future__ import annotations

from dataclasses import dataclass

from app.schemas.hotpost import HotpostQueryParse, HotpostSearchRequest
from app.services.hotpost.query_resolver import HotpostQueryResolution
from app.services.hotpost.rant_evidence_helpers import build_focus_terms


@dataclass(frozen=True)
class RealtimeComparePolicy:
    initial_query_parts_limit_cap: int = 2
    initial_subreddits_limit_cap: int = 4
    max_posts_per_subreddit_cap: int = 12
    max_comment_posts_cap: int = 6
    max_comments_per_post_cap: int = 12
    disable_remediation: bool = True
    disable_reasoning_retry: bool = True
    disable_report_generation: bool = True


def _normalize_text(value:Optional[ str]) -> str:
    return str(value or "").strip()


def _has_compare_pair(query_parse:Optional[ HotpostQueryParse]) -> bool:
    if query_parse is None or query_parse.query_kind != "compare":
        return False
    return bool(_normalize_text(query_parse.subject) and _normalize_text(query_parse.compare_target))


def _focus_search_terms(
    *,
    request_query: str,
    subject: str,
    compare_target: str,
    focus: str,
    scenario: str,
) -> list[str]:
    hint_source = " ".join(part for part in [focus, scenario] if part).strip()
    expanded = build_focus_terms(
        query=request_query,
        keywords=[subject, compare_target],
        focus_hint=hint_source,
    )
    multi_word_ascii = [term for term in expanded if term.isascii() and " " in term]
    single_word_ascii = [term for term in expanded if term.isascii() and " " not in term]
    cjk_terms = [term for term in expanded if not term.isascii()]
    ordered = multi_word_ascii + single_word_ascii + cjk_terms
    seen: set[str] = set()
    terms: list[str] = []
    for term in ordered:
        normalized = _normalize_text(term).lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        terms.append(term)
        if len(terms) >= 4:
            break
    return terms


def resolve_realtime_compare_policy(
    *,
    mode: str,
    request: HotpostSearchRequest,
) ->Optional[ RealtimeComparePolicy]:
    if str(mode).strip().lower() != "rant":
        return None
    if not _has_compare_pair(request.query_parse_override):
        return None
    # 用户已经在前端确认过 compare 标签时，首屏直接走轻链路，不再放大实时预算。
    return RealtimeComparePolicy()


def build_query_resolution_from_override(
    *,
    request_query: str,
    query_parse: HotpostQueryParse,
) -> HotpostQueryResolution:
    subject = _normalize_text(query_parse.subject)
    compare_target = _normalize_text(query_parse.compare_target)
    focus = _normalize_text(query_parse.focus)
    scenario = _normalize_text(query_parse.scenario)

    focus_terms = _focus_search_terms(
        request_query=request_query,
        subject=subject,
        compare_target=compare_target,
        focus=focus,
        scenario=scenario,
    )
    keywords = [term for term in [subject, compare_target, *focus_terms, focus, scenario] if term]
    parts = [f"{subject} vs {compare_target}".strip()] if subject and compare_target else []
    parts.extend(focus_terms[:2])
    if not focus_terms and focus:
        parts.append(focus)
    if scenario and scenario not in parts:
        parts.append(scenario)
    search_query = " ".join(parts).strip() or request_query.strip()
    return HotpostQueryResolution(
        original_query=request_query,
        search_query=search_query,
        keywords=keywords,
        subreddits=[],
        source="original",
    )


__all__ = [
    "RealtimeComparePolicy",
    "build_query_resolution_from_override",
    "resolve_realtime_compare_policy",
]
