from __future__ import annotations

from typing import Optional, Any

from app.services.hotpost.quote_projection import build_voice_first_top_quotes
from app.services.hotpost.rant_claim_grounding import (
    build_rant_summary_claim_trace,
    resolve_rant_render_mode,
)
from app.services.hotpost.rant_facets import build_rant_complaint_facets
from app.services.hotpost.rant_evidence_cards import (
    collect_rant_evidence_units,
    scope_rant_evidence_units,
)
from app.services.hotpost.rant_evidence_helpers import looks_like_complaint_quote
from app.services.hotpost.rant_evidence_metrics import build_rant_evidence_metrics
from app.services.hotpost.rant_mode_summaries import (
    build_compare_insufficient_summary,
    build_compare_no_hit_summary,
    build_compare_rant_summary,
    build_grounded_rant_summary,
    build_quote_only_rant_summary,
)
from app.services.hotpost.response_bundle_common import HotpostResponseBundleInput, get_payload_value
from app.services.hotpost.rules import normalize_text


def finalize_rant_payload(
    bundle: HotpostResponseBundleInput,
    payload: dict[str, Any],
    *,
    mode_state: str,
    pre_mode_payload: dict[str, Any],
    pre_projection_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    evidence_payload = _build_evidence_payload(
        bundle=bundle,
        payload=payload,
        pre_mode_payload=pre_mode_payload,
        pre_projection_payload=pre_projection_payload,
    )
    raw_evidence_units = collect_rant_evidence_units(
        evidence_payload,
        complaint_facets=[],
        query=bundle.query,
        keywords=bundle.keywords,
        query_family=bundle.query_family,
    )
    scoped_evidence_units = scope_rant_evidence_units(
        evidence_units=raw_evidence_units,
        query=bundle.query,
        query_family=bundle.query_family,
    )
    if not scoped_evidence_units and normalize_text(bundle.query_family or "") != "comparison_complaint_discovery":
        scoped_evidence_units = raw_evidence_units

    voice_quote_limit = 3 if mode_state in {"preview", "no_hit"} else 5
    # 第一屏先给原话，后面的 compare/summary 只能围绕这层证据继续组织。
    payload["top_quotes"] = build_voice_first_top_quotes(
        scoped_evidence_units,
        limit=voice_quote_limit,
        complaint_detector=looks_like_complaint_quote,
    )
    complaint_facets = build_rant_complaint_facets(
        evidence_payload,
        query=bundle.query,
        keywords=bundle.keywords,
        query_family=bundle.query_family,
    )
    render_mode = resolve_rant_render_mode(
        payload=evidence_payload,
        query=bundle.query,
        keywords=bundle.keywords,
        query_family=bundle.query_family,
        complaint_facets=complaint_facets,
    )
    rant_metrics = build_rant_evidence_metrics(
        evidence_payload,
        complaint_facets=complaint_facets,
        query=bundle.query,
        keywords=bundle.keywords,
        query_family=bundle.query_family,
    )
    payload["complaint_facets"] = complaint_facets
    payload["render_mode"] = render_mode

    summary = _build_evidence_first_summary(
        render_mode=render_mode,
        complaint_facets=complaint_facets,
        payload=payload,
        query=bundle.query,
        keywords=bundle.keywords,
    )
    if summary:
        payload["summary"] = summary

    claim_trace = build_rant_summary_claim_trace(
        render_mode=render_mode,
        complaint_facets=complaint_facets,
        payload=payload,
        query=bundle.query,
        keywords=bundle.keywords,
    )
    return _apply_rant_fallbacks(
        payload=payload,
        rant_metrics=rant_metrics,
        claim_trace=claim_trace,
        complaint_facets=complaint_facets,
        query=bundle.query,
        keywords=bundle.keywords,
    )


def _build_evidence_payload(
    *,
    bundle: HotpostResponseBundleInput,
    payload: dict[str, Any],
    pre_mode_payload: dict[str, Any],
    pre_projection_payload: dict[str, Any],
) -> dict[str, Any]:
    evidence_payload = dict(payload)
    compare_requested = normalize_text(bundle.query_family or "") == "comparison_complaint_discovery"
    if compare_requested:
        evidence_payload["top_posts"] = bundle.top_posts
        evidence_payload["top_quotes"] = list(
            pre_mode_payload.get("top_quotes")
            or pre_projection_payload.get("top_quotes")
            or payload.get("top_quotes")
            or []
        )
    return evidence_payload


def _build_evidence_first_summary(
    *,
    render_mode: str,
    complaint_facets: list[Any],
    payload: dict[str, Any],
    query: str,
    keywords: list[str],
) ->Optional[ str]:
    if render_mode == "compare":
        return build_compare_rant_summary(
            complaint_facets,
            query=query,
            keywords=keywords,
            payload=payload,
            get_payload_value=get_payload_value,
        )
    if render_mode == "insufficient_evidence":
        return build_compare_insufficient_summary(payload=payload, get_payload_value=get_payload_value)
    if render_mode == "no_hit":
        return build_compare_no_hit_summary()
    if render_mode == "quote_only":
        return build_quote_only_rant_summary(
            complaint_facets,
            payload=payload,
            get_payload_value=get_payload_value,
        )
    return build_grounded_rant_summary(complaint_facets)


def _apply_rant_fallbacks(
    *,
    payload: dict[str, Any],
    rant_metrics: dict[str, Any],
    claim_trace: list[dict[str, Any]],
    complaint_facets: list[Any],
    query: str,
    keywords: list[str],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    render_mode = str(payload.get("render_mode") or "")
    if render_mode == "compare" and len(claim_trace) < 2:
        payload["render_mode"] = "insufficient_evidence"
        fallback = build_compare_insufficient_summary(payload=payload, get_payload_value=get_payload_value)
        if fallback:
            payload["summary"] = fallback
        rant_metrics["insufficient_reason"] = str(rant_metrics.get("insufficient_reason") or "compare_claims_not_grounded")
        claim_trace = build_rant_summary_claim_trace(
            render_mode="insufficient_evidence",
            complaint_facets=complaint_facets,
            payload=payload,
            query=query,
            keywords=keywords,
        )
    elif render_mode == "grounded_summary" and not claim_trace:
        payload["render_mode"] = "quote_only"
        fallback = build_quote_only_rant_summary(
            complaint_facets,
            payload=payload,
            get_payload_value=get_payload_value,
        )
        if fallback:
            payload["summary"] = fallback
        rant_metrics["insufficient_reason"] = str(rant_metrics.get("insufficient_reason") or "summary_claims_not_grounded")
        claim_trace = build_rant_summary_claim_trace(
            render_mode="quote_only",
            complaint_facets=complaint_facets,
            payload=payload,
            query=query,
            keywords=keywords,
        )
    return payload, rant_metrics, claim_trace
