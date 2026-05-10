from __future__ import annotations

from typing import Optional, Any

from app.schemas.hotpost import ComplaintFacet
from app.services.hotpost.compare_targets import infer_compare_targets
from app.services.hotpost.rant_evidence_helpers import get_payload_value
from app.services.hotpost.rant_evidence_metrics import build_rant_evidence_metrics
from app.services.hotpost.rules import normalize_text


def match_quote_ids_for_claim(
    *,
    facet:Optional[ ComplaintFacet],
    top_quotes: list[Any],
) -> list[str]:
    if not top_quotes:
        return []
    matched_ids: list[str] = []
    quote_text = normalize_text(facet.representative_quote if facet else "")
    label_text = normalize_text(facet.label if facet else "")
    target_text = normalize_text(facet.target if facet else "")
    for quote in top_quotes:
        quote_id = str(get_payload_value(quote, "quote_id") or "").strip()
        if not quote_id or quote_id in matched_ids:
            continue
        normalized_quote = normalize_text(get_payload_value(quote, "quote"))
        if quote_text and quote_text == normalized_quote:
            matched_ids.append(quote_id)
            continue
        if label_text and label_text in normalized_quote:
            matched_ids.append(quote_id)
            continue
        if target_text and target_text in normalized_quote:
            matched_ids.append(quote_id)
        if len(matched_ids) >= 2:
            break
    return matched_ids[:2] if len(matched_ids) >= 2 else []


def match_quote_ids_for_target(
    *,
    target: str,
    top_quotes: list[Any],
) -> list[str]:
    if not top_quotes:
        return []
    normalized_target = normalize_text(target)
    if not normalized_target:
        return []
    matched_ids: list[str] = []
    for quote in top_quotes:
        quote_id = str(get_payload_value(quote, "quote_id") or "").strip()
        if not quote_id or quote_id in matched_ids:
            continue
        normalized_quote = normalize_text(get_payload_value(quote, "quote"))
        if normalized_target in normalized_quote:
            matched_ids.append(quote_id)
        if len(matched_ids) >= 2:
            break
    return matched_ids[:2] if len(matched_ids) >= 2 else []


def build_rant_summary_claim_trace(
    *,
    render_mode: str,
    complaint_facets: list[ComplaintFacet],
    payload: dict[str, Any],
    query: str,
    keywords: list[str],
) -> list[dict[str, Any]]:
    top_quotes = list(payload.get("top_quotes") or [])
    fallback_quote_ids = [
        str(get_payload_value(quote, "quote_id") or "").strip()
        for quote in top_quotes
        if str(get_payload_value(quote, "quote_id") or "").strip()
    ]
    if not fallback_quote_ids:
        return []

    if render_mode == "quote_only":
        return [{"claim": "quote_only", "quote_ids": fallback_quote_ids[:2]}]
    if render_mode == "insufficient_evidence":
        return [{"claim": "insufficient_evidence", "quote_ids": fallback_quote_ids[:2]}]
    if render_mode == "no_hit":
        return []

    if render_mode == "compare":
        compare_targets = infer_compare_targets(query, keywords)
        if len(compare_targets) < 2:
            return []
        trace: list[dict[str, Any]] = []
        for target, claim in (
            (compare_targets[0], f"为什么更喜欢 {compare_targets[0]}"),
            (compare_targets[1], f"为什么会嫌弃 {compare_targets[1]}"),
        ):
            target_facet = next(
                (facet for facet in complaint_facets if normalize_text(facet.target or "") == normalize_text(target)),
                None,
            )
            quote_ids = match_quote_ids_for_claim(
                facet=target_facet,
                top_quotes=top_quotes,
            )
            if len(quote_ids) < 2:
                quote_ids = match_quote_ids_for_target(
                    target=target,
                    top_quotes=top_quotes,
                )
            if len(quote_ids) >= 2:
                trace.append({"claim": claim, "quote_ids": quote_ids})
        return trace

    # summary 不是自由发挥，而是从已命中的 quote id 倒推可说的话。
    trace: list[dict[str, Any]] = []
    for facet in complaint_facets[:2]:
        quote_ids = match_quote_ids_for_claim(
            facet=facet,
            top_quotes=top_quotes,
        )
        if len(quote_ids) >= 2:
            trace.append({"claim": facet.label, "quote_ids": quote_ids})
    return trace


def resolve_rant_render_mode(
    *,
    payload: dict[str, Any],
    query: str,
    keywords: list[str],
    query_family:Optional[ str],
    complaint_facets: list[ComplaintFacet],
) -> str:
    normalized_query = normalize_text(query)
    normalized_family = normalize_text(query_family or "")
    metrics = build_rant_evidence_metrics(
        payload,
        complaint_facets=complaint_facets,
        query=query,
        keywords=keywords,
        query_family=query_family,
    )
    if normalized_family == "comparison_complaint_discovery" or " vs " in normalized_query or " 比 " in query:
        if int(metrics.get("valid_quote_count") or 0) <= 0:
            return "no_hit"
        if bool(metrics.get("compare_ready")):
            return "compare"
        return "insufficient_evidence"
    if (
        len(complaint_facets) <= 1
        or int(metrics.get("valid_quote_count") or 0) < 4
        or int(metrics.get("unique_thread_count") or 0) < 2
    ):
        return "quote_only"
    return "grounded_summary"
