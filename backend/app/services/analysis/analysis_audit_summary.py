from __future__ import annotations

from typing import Optional, Any, Mapping


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _is_clickable_reddit_url(url: Any) -> bool:
    lowered = str(url or "").strip().lower()
    return lowered.startswith(("http://", "https://")) and "reddit.com/" in lowered


def _collect_clickable_reddit_links(section_items: Any) -> list[str]:
    links: list[str] = []
    for item in _list(section_items):
        if not isinstance(item, Mapping):
            continue
        for evidence in _list(item.get("evidence_chain")):
            if not isinstance(evidence, Mapping):
                continue
            url = str(evidence.get("url") or "").strip()
            if _is_clickable_reddit_url(url):
                links.append(url)
    return list(dict.fromkeys(links))


def build_analysis_audit_summary(
    *,
    sources: Mapping[str, Any],
    report_tier: str,
    analysis_blocked:Optional[ str],
) -> dict[str, Any]:
    diagnostics = _mapping(sources.get("analysis_diagnostics"))
    query_plan = _mapping(diagnostics.get("query_plan"))
    route = _mapping(diagnostics.get("open_topic_route"))
    drift_guard = _mapping(diagnostics.get("drift_guard"))
    facts_quality = _mapping(sources.get("facts_v2_quality"))
    facts_metrics = _mapping(facts_quality.get("metrics"))
    structured = _mapping(sources.get("report_structured"))

    pain_links = _collect_clickable_reddit_links(structured.get("pain_points"))
    opportunity_links = _collect_clickable_reddit_links(structured.get("opportunities"))
    unique_links = list(dict.fromkeys([*pain_links, *opportunity_links]))

    reason_code = "passed"
    if analysis_blocked:
        reason_code = (
            "facts_quality_fail"
            if analysis_blocked
            in {"quality_gate_blocked", "scouting_brief", "insufficient_samples"}
            else "runtime_fail"
        )
    elif not pain_links or not opportunity_links or len(unique_links) < 2:
        reason_code = "evidence_link_density_fail"
    elif report_tier == "A_full":
        reason_code = "passed"
    elif drift_guard.get("action"):
        reason_code = "drift_intervened"
    elif query_plan and not route:
        reason_code = "route_fail"
    elif sources.get("reddit_api_failures") and not int(sources.get("posts_analyzed") or 0):
        reason_code = "runtime_fail"

    if reason_code == "passed":
        summary = f"{report_tier}；主链通过，证据链接达标。"
    elif reason_code == "facts_quality_fail":
        summary = f"{report_tier}；当前卡在事实质量门槛（{analysis_blocked or 'quality_gate_blocked'}）。"
    elif reason_code == "drift_intervened":
        summary = f"{report_tier}；drift guard 介入，route 被放松。"
    elif reason_code == "evidence_link_density_fail":
        summary = (
            f"{report_tier}；报告证据链接不足，pain={len(pain_links)}，"
            f"opportunity={len(opportunity_links)}，unique={len(unique_links)}。"
        )
    elif reason_code == "route_fail":
        summary = f"{report_tier}；query plan 已生成，但 route 没稳定落地。"
    else:
        summary = f"{report_tier}；运行时异常导致结果不可信。"

    return {
        "query_plan_summary": {
            "intent": str(query_plan.get("intent") or ""),
            "route_query_en": str(query_plan.get("route_query_en") or ""),
            "retrieve_queries_en": _list(query_plan.get("retrieve_queries_en")),
            "must_keep": _list(query_plan.get("must_keep")),
            "must_not_invent": _list(query_plan.get("must_not_invent")),
        },
        "route_decision_summary": {
            "warzone": str(route.get("warzone") or ""),
            "confidence": route.get("confidence"),
            "margin": route.get("margin"),
            "seed_communities": _list(route.get("seed_communities")),
            "candidate_warzones": _list(route.get("candidate_warzones")),
        },
        "drift_guard_summary": {
            "action": str(drift_guard.get("action") or ""),
            "initial_reasons": _list(_mapping(drift_guard.get("initial")).get("reasons")),
            "retrieval_reasons": _list(_mapping(drift_guard.get("retrieval")).get("reasons")),
            "route_share": _mapping(drift_guard.get("retrieval")).get("route_share"),
            "route_hits": _mapping(drift_guard.get("retrieval")).get("route_hits"),
            "retrieval_total": _mapping(drift_guard.get("retrieval")).get("retrieval_total"),
            "top_retrieval_communities": _list(_mapping(drift_guard.get("retrieval")).get("top_retrieval_communities")),
        },
        "facts_quality_summary": {
            "tier": str(facts_quality.get("tier") or report_tier),
            "passed": bool(facts_quality.get("passed")),
            "flags": _list(facts_quality.get("flags")),
            "coverage_tier": facts_metrics.get("coverage_tier"),
            "source_signal_volume": facts_metrics.get("source_signal_volume"),
            "good_pains": facts_metrics.get("good_pains"),
            "good_brands": facts_metrics.get("good_brands"),
            "solutions": facts_metrics.get("solutions"),
            "min_solutions_effective": facts_metrics.get("min_solutions_effective"),
        },
        "final_verdict": {
            "reason_code": reason_code,
            "report_tier": report_tier,
            "analysis_blocked": analysis_blocked or "",
            "pain_clickable_reddit_links": len(pain_links),
            "opportunity_clickable_reddit_links": len(opportunity_links),
            "unique_clickable_reddit_links": len(unique_links),
            "summary": summary,
        },
    }


__all__ = ["build_analysis_audit_summary"]
