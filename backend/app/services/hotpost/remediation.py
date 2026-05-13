from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Iterable

from app.services.hotpost.hotpost_config import load_default_hotpost_runtime_config
from app.utils.subreddit import normalize_subreddit_name


@dataclass(frozen=True, slots=True)
class HotpostRemediationPlan:
    query_parts: list[str]
    subreddits: list[str]
    added_terms: list[str]
    notes: list[str]


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def _normalize_subreddits(items: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for item in items:
        normalized = normalize_subreddit_name(item)
        if not normalized:
            continue
        cleaned.append(normalized)
    return _dedupe(cleaned)


def build_hotpost_remediation_plan(
    *,
    mode: str,
    search_query: str,
    base_query_parts: list[str],
    base_subreddits: list[str],
    gaps: list[str],
) ->Optional[ HotpostRemediationPlan]:
    settings = load_default_hotpost_runtime_config().remediation
    if not settings.enabled or settings.max_rounds <= 0:
        return None
    normalized_mode = str(mode or "").strip().lower()
    normalized_gaps = [
        str(gap or "").strip().lower()
        for gap in gaps
        if str(gap or "").strip()
    ]
    if not normalized_gaps:
        return None

    mode_terms = list(settings.mode_terms.get(normalized_mode, []))
    gap_terms: list[str] = []
    for gap in normalized_gaps:
        gap_terms.extend(settings.gap_terms.get(gap, []))

    search_query_lower = str(search_query or "").strip().lower()
    candidate_terms = [
        term
        for term in _dedupe(mode_terms + gap_terms)
        if term and term.lower() not in search_query_lower
    ]
    added_terms = candidate_terms[: settings.max_added_query_parts]

    normalized_parts = _dedupe(base_query_parts or [search_query])
    extra_parts = [f"{search_query} {term}".strip() for term in added_terms]
    query_parts = _dedupe(normalized_parts + extra_parts)

    normalized_subreddits = _normalize_subreddits(base_subreddits)
    hint_subreddits = _normalize_subreddits(settings.subreddit_hints.get(normalized_mode, []))
    additional_subreddits = [
        subreddit
        for subreddit in hint_subreddits
        if subreddit not in normalized_subreddits
    ][: settings.max_added_subreddits]
    subreddits = normalized_subreddits + additional_subreddits

    if query_parts == normalized_parts and not additional_subreddits:
        return None

    notes = [f"质量缺口触发自动补证: {', '.join(normalized_gaps)}"]
    if added_terms:
        notes.append(f"自动扩展查询词: {', '.join(added_terms)}")
    if additional_subreddits:
        notes.append(f"自动扩展社区: {', '.join(additional_subreddits)}")

    return HotpostRemediationPlan(
        query_parts=query_parts,
        subreddits=subreddits,
        added_terms=added_terms,
        notes=notes,
    )


__all__ = ["HotpostRemediationPlan", "build_hotpost_remediation_plan"]
