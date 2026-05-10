from __future__ import annotations

from collections import Counter
from typing import Optional, Any

from app.schemas.hotpost import ComplaintFacet
from app.services.hotpost.compare_evidence_matrix import build_compare_evidence_matrix
from app.services.hotpost.compare_targets import infer_compare_targets
from app.services.hotpost.rant_evidence_cards import (
    collect_rant_evidence_units,
    scope_rant_evidence_units,
)
from app.services.hotpost.rant_evidence_helpers import (
    build_focus_terms,
    extract_focus_hint,
    focus_matches_quote,
    normalize_thread_key,
)
from app.services.hotpost.rules import normalize_text


def build_rant_evidence_metrics(
    payload: dict[str, Any],
    *,
    complaint_facets: list[ComplaintFacet],
    query: str,
    keywords: list[str],
    query_family:Optional[ str],
) -> dict[str, Any]:
    evidence_units = collect_rant_evidence_units(
        payload,
        complaint_facets=complaint_facets,
        query=query,
        keywords=keywords,
        query_family=query_family,
    )
    all_valid_units = [unit for unit in evidence_units if bool(unit.get("valid"))]
    valid_units = scope_rant_evidence_units(
        evidence_units=evidence_units,
        query=query,
        query_family=query_family,
    )
    side_resolution_sources = _count_resolution_sources(
        units=all_valid_units,
        field="side_resolution_source",
    )
    focus_resolution_sources = _count_resolution_sources(
        units=all_valid_units,
        field="focus_resolution_source",
    )
    focus_bundle_hits = _collect_focus_bundle_hits(
        payload=payload,
        valid_units=valid_units,
        query=query,
        keywords=keywords,
    )
    # compare 的成败只看 evidence card 覆盖，不再被帖子级过滤提前判死。
    compare_matrix = build_compare_evidence_matrix(
        evidence_cards=valid_units,
        query=query,
        keywords=keywords,
        query_family=query_family,
    )
    if compare_matrix is not None:
        return {
            "valid_quote_count": compare_matrix.valid_evidence_count,
            "valid_evidence_cards": compare_matrix.valid_evidence_count,
            "unique_thread_count": compare_matrix.unique_thread_count,
            "insufficient_reason": compare_matrix.insufficient_reason,
            "no_hit_reason": (
                compare_matrix.insufficient_reason
                if compare_matrix.render_mode == "no_hit"
                else None
            ),
            "compare_ready": compare_matrix.render_mode == "compare",
            "compare_left_count": compare_matrix.left_count,
            "compare_right_count": compare_matrix.right_count,
            "side_resolution_sources": side_resolution_sources,
            "focus_resolution_sources": focus_resolution_sources,
            "focus_bundle_hits": focus_bundle_hits,
        }

    unique_threads = {
        normalize_thread_key(unit.get("thread_key") or unit.get("url") or unit.get("quote"))
        for unit in valid_units
        if normalize_thread_key(unit.get("thread_key") or unit.get("url") or unit.get("quote"))
    }
    compare_targets = infer_compare_targets(query, keywords)
    compare_requested = normalize_text(query_family or "") == "comparison_complaint_discovery"
    target_counts: Counter[str] = Counter()
    for unit in valid_units:
        normalized_target = normalize_thread_key(unit.get("side") or unit.get("target"))
        if normalized_target:
            target_counts[normalized_target] += 1

    insufficient_reason:Optional[ str] = None
    compare_ready = False
    left_count = 0
    right_count = 0
    if len(compare_targets) >= 2:
        left_count = int(target_counts.get(normalize_text(compare_targets[0]), 0))
        right_count = int(target_counts.get(normalize_text(compare_targets[1]), 0))
        compare_ready = left_count >= 2 and right_count >= 2 and len(unique_threads) >= 3
        if compare_requested:
            if not valid_units:
                insufficient_reason = "no_valid_compare_evidence"
            elif left_count < 2 or right_count < 2:
                insufficient_reason = "compare_sides_incomplete"
            elif len(unique_threads) < 3:
                insufficient_reason = "compare_threads_below_threshold"
    if not compare_requested:
        if len(valid_units) < 4:
            insufficient_reason = "valid_quotes_below_threshold"
        elif len(unique_threads) < 2:
            insufficient_reason = "unique_threads_below_threshold"

    return {
        "valid_quote_count": len(valid_units),
        "valid_evidence_cards": len(valid_units),
        "unique_thread_count": len(unique_threads),
        "insufficient_reason": insufficient_reason,
        "no_hit_reason": insufficient_reason if compare_requested and not valid_units else None,
        "compare_ready": compare_ready,
        "compare_left_count": left_count,
        "compare_right_count": right_count,
        "side_resolution_sources": side_resolution_sources,
        "focus_resolution_sources": focus_resolution_sources,
        "focus_bundle_hits": focus_bundle_hits,
    }


def _count_resolution_sources(
    *,
    units: list[dict[str, Any]],
    field: str,
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for unit in units:
        source = str(unit.get(field) or "").strip()
        if source:
            counts[source] += 1
    return dict(counts)


def _collect_focus_bundle_hits(
    *,
    payload: dict[str, Any],
    valid_units: list[dict[str, Any]],
    query: str,
    keywords: list[str],
) -> list[str]:
    focus_terms = build_focus_terms(
        query=query,
        keywords=keywords,
        focus_hint=extract_focus_hint(payload),
    )
    if not focus_terms or not valid_units:
        return []

    normalized_quotes = [
        normalize_text(str(unit.get("quote") or ""))
        for unit in valid_units
        if str(unit.get("quote") or "").strip()
    ]
    hits: list[str] = []
    for term in focus_terms:
        if any(
            focus_matches_quote(
                normalized_quote=normalized_quote,
                focus_terms=[term],
            )
            for normalized_quote in normalized_quotes
        ):
            hits.append(term)
    return hits[:8]
