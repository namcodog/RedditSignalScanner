from __future__ import annotations

import os
from typing import Optional, Any

from app.schemas.hotpost import HotpostSearchResponse
from app.services.hotpost.preview_projection import apply_hotpost_preview_projection
from app.services.hotpost.quality_contract import apply_hotpost_quality_contract
from app.services.hotpost.report_export import export_markdown_report
from app.services.hotpost.report_llm import (
    apply_hotpost_llm_annotations,
    merge_hotpost_llm_report,
)
from app.services.hotpost.response_bundle_common import (
    HotpostResponseBundleInput,
    build_hotpost_debug_info,
    resolve_hotpost_response,
)
from app.services.hotpost.response_bundle_payload import (
    apply_mode_payload_enrichment,
    build_base_response_payload,
    build_next_steps_payload,
)
from app.services.hotpost.response_bundle_rant import finalize_rant_payload
from app.services.hotpost.mode_contract import apply_hotpost_mode_contract


def _classify_compare_boundary(
    *,
    bundle: HotpostResponseBundleInput,
    rant_metrics: dict[str, Any],
) ->Optional[ tuple[bool]Optional[, str]]:
    if bundle.query_family != "comparison_complaint_discovery":
        return None, None
    valid_evidence_cards = int(rant_metrics.get("valid_evidence_cards") or rant_metrics.get("valid_quote_count") or 0)
    left_count = int(rant_metrics.get("compare_left_count") or 0)
    right_count = int(rant_metrics.get("compare_right_count") or 0)
    raw_posts = int(bundle.raw_posts or 0)
    lane_hits = sum(int(value or 0) for value in dict(bundle.lane_yield or {}).values())
    comment_dive_count = int(bundle.comment_dive_count or 0)
    focus_hits = list(rant_metrics.get("focus_bundle_hits") or [])

    if valid_evidence_cards == 0:
        if raw_posts == 0 and lane_hits == 0:
            return True, "reddit_sparse_for_focus"
        if raw_posts > 0 and comment_dive_count > 0:
            return True, "related_discussion_without_explicit_compare_evidence"
        return False, "retrieval_gap_before_evidence"

    if left_count < 2 or right_count < 2:
        if comment_dive_count > 0 and focus_hits:
            return True, "single_sided_reddit_evidence"
        return False, "retrieval_gap_side_or_focus"

    return True, None


def build_hotpost_search_response(bundle: HotpostResponseBundleInput) -> HotpostSearchResponse:
    status_value, degraded_reasons = resolve_hotpost_response(
        resolution_reason=bundle.resolution_reason,
        summary_result=bundle.summary_result,
        report_result=bundle.report_result,
    )
    debug_info = build_hotpost_debug_info(
        resolution_source=bundle.resolution_source,
        resolution_reason=bundle.resolution_reason,
        query_intent=bundle.query_intent,
        query_family=bundle.query_family,
        primary_friction=bundle.primary_friction,
        secondary_frictions=bundle.secondary_frictions,
        search_query=bundle.search_query,
        query_parts=bundle.query_parts,
        retrieval_hypotheses=bundle.retrieval_hypotheses,
        keywords=bundle.keywords,
        expanded_terms=bundle.expanded_terms,
        negative_terms=bundle.negative_terms,
        forbidden_narrowing_terms=bundle.forbidden_narrowing_terms,
        candidate_subreddits=bundle.candidate_subreddits,
        positive_intent_terms=bundle.positive_intent_terms,
        forbidden_context_terms=bundle.forbidden_context_terms,
        domain_terms=bundle.domain_terms,
        search_strategy=bundle.search_strategy,
        time_filter=bundle.time_filter,
        sort=bundle.sort,
        subreddits=bundle.subreddits,
        raw_posts=bundle.raw_posts,
        filtered_posts=bundle.filtered_posts,
        relevance_filtered=bundle.relevance_filtered,
        relevant_posts=bundle.relevant_posts,
        voice_hits=0,
        summary_result=bundle.summary_result,
        report_result=bundle.report_result,
        degraded_reasons=degraded_reasons,
        response_source="live",
    )
    payload, evidence_count = build_base_response_payload(bundle, status_value=status_value, debug_info=debug_info)
    payload = merge_hotpost_llm_report(payload, bundle.report_result.report)
    payload = apply_hotpost_llm_annotations(payload, bundle.report_result.report)
    payload = apply_mode_payload_enrichment(bundle, payload, evidence_count=evidence_count)
    payload["next_steps"] = build_next_steps_payload(bundle, payload)

    contract = apply_hotpost_quality_contract(
        payload=payload,
        mode=bundle.mode,
        top_posts=bundle.top_posts,
        keywords=bundle.keywords,
    )
    payload = contract.payload
    payload["notes"] = _merge_contract_notes(payload, contract.notes)

    pre_mode_payload = dict(payload)
    payload, mode_state, mode_state_reasons, reliability_note, mode_metrics = apply_hotpost_mode_contract(
        mode=bundle.mode,
        payload=payload,
        top_posts=bundle.top_posts,
        positive_intent_terms=bundle.positive_intent_terms,
        domain_terms=bundle.domain_terms,
        raw_posts=bundle.raw_posts,
        relevance_filtered=bundle.relevance_filtered,
        relevant_posts=bundle.relevant_posts,
    )
    pre_projection_payload = dict(payload)
    payload = apply_hotpost_preview_projection(mode=bundle.mode, state=mode_state, payload=payload)
    payload["reliability_note"] = reliability_note

    if bundle.mode == "rant":
        payload, rant_metrics, summary_claim_trace = finalize_rant_payload(
            bundle,
            payload,
            mode_state=mode_state,
            pre_mode_payload=pre_mode_payload,
            pre_projection_payload=pre_projection_payload,
        )
    else:
        rant_metrics = {}
        summary_claim_trace = []

    payload["debug_info"] = _build_runtime_debug_info(
        bundle=bundle,
        payload=payload,
        contract=contract,
        mode_state=mode_state,
        mode_state_reasons=mode_state_reasons,
        mode_metrics=mode_metrics,
        rant_metrics=rant_metrics,
        summary_claim_trace=summary_claim_trace,
    )
    if (contract.gaps or mode_state == "no_hit") and str(payload.get("status") or "").strip().lower() == "completed":
        payload["status"] = "degraded"
    if os.getenv("ENABLE_HOTPOST_MARKDOWN_EXPORT", "true").strip().lower() in {"1", "true", "yes"}:
        payload["markdown_report"] = export_markdown_report(payload)
    return HotpostSearchResponse(**payload)


def _merge_contract_notes(payload: dict[str, Any], contract_notes: list[str]) -> list[str]:
    existing_notes = list(payload.get("notes") or [])
    for note in contract_notes:
        if note not in existing_notes:
            existing_notes.append(note)
    return existing_notes


def _build_runtime_debug_info(
    *,
    bundle: HotpostResponseBundleInput,
    payload: dict[str, Any],
    contract: Any,
    mode_state: str,
    mode_state_reasons: list[str],
    mode_metrics: dict[str, Any],
    rant_metrics: dict[str, Any],
    summary_claim_trace: list[dict[str, Any]],
) -> dict[str, Any]:
    debug_info_payload = payload.get("debug_info")
    if hasattr(debug_info_payload, "model_dump"):
        debug_info_data = debug_info_payload.model_dump()
    elif isinstance(debug_info_payload, dict):
        debug_info_data = dict(debug_info_payload)
    else:
        debug_info_data = {}

    debug_info_data["quality_contract_gaps"] = list(contract.gaps)
    debug_info_data["mode_state"] = mode_state
    debug_info_data["mode_state_reasons"] = list(mode_state_reasons)
    debug_info_data["relevant_posts"] = int(bundle.relevant_posts or mode_metrics.get("evidence_posts") or 0)
    if bundle.mode == "rant":
        debug_info_data["voice_hits"] = int(rant_metrics.get("valid_quote_count") or 0)
        debug_info_data["valid_quote_count"] = int(rant_metrics.get("valid_quote_count") or 0)
        debug_info_data["valid_evidence_cards"] = int(
            rant_metrics.get("valid_evidence_cards") or rant_metrics.get("valid_quote_count") or 0
        )
        debug_info_data["unique_thread_count"] = int(rant_metrics.get("unique_thread_count") or 0)
        debug_info_data["focus_bundle_hits"] = list(rant_metrics.get("focus_bundle_hits") or [])
        debug_info_data["side_resolution_sources"] = dict(rant_metrics.get("side_resolution_sources") or {})
        debug_info_data["focus_resolution_sources"] = dict(rant_metrics.get("focus_resolution_sources") or {})
        debug_info_data["lane_yield"] = dict(bundle.lane_yield or {})
        debug_info_data["comment_dive_count"] = int(bundle.comment_dive_count or 0)
        if bundle.query_family == "comparison_complaint_discovery":
            debug_info_data["side_A_count"] = int(rant_metrics.get("compare_left_count") or 0)
            debug_info_data["side_B_count"] = int(rant_metrics.get("compare_right_count") or 0)
            no_hit_reason = str(rant_metrics.get("no_hit_reason") or "").strip()
            debug_info_data["no_hit_reason"] = no_hit_reason or None
            search_exhausted, boundary_reason = _classify_compare_boundary(bundle=bundle, rant_metrics=rant_metrics)
            debug_info_data["search_exhausted"] = search_exhausted
            debug_info_data["boundary_reason"] = boundary_reason
    else:
        debug_info_data["voice_hits"] = int(mode_metrics.get("strong_quotes") or 0)
        debug_info_data["valid_quote_count"] = int(mode_metrics.get("strong_quotes") or 0)
        debug_info_data["valid_evidence_cards"] = int(mode_metrics.get("strong_quotes") or 0)
        debug_info_data["unique_thread_count"] = int(rant_metrics.get("unique_thread_count") or 0)
    debug_info_data["mode_decision"] = str(payload.get("render_mode") or mode_state or "")
    debug_info_data["insufficient_reason"] = str(rant_metrics.get("insufficient_reason") or "")
    debug_info_data["render_mode"] = str(payload.get("render_mode") or "")
    debug_info_data["summary_claim_to_quote_ids"] = list(summary_claim_trace)

    degraded = list(debug_info_data.get("degraded_reasons") or [])
    for gap in contract.gaps:
        marker = f"quality_contract:{gap}"
        if marker not in degraded:
            degraded.append(marker)
    for reason in mode_state_reasons:
        marker = f"mode_state:{reason}"
        if marker not in degraded:
            degraded.append(marker)
    debug_info_data["degraded_reasons"] = degraded
    return debug_info_data
