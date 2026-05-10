from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any, Callable, Mapping, Sequence


@dataclass(slots=True)
class AnalysisOutputArtifacts:
    evidence_ledger:Optional[ dict[str, Any]]
    facts_slice:Optional[ dict[str, Any]]
    knowledge_graph:Optional[ dict[str, Any]]


def build_knowledge_graph(
    *,
    aggregates:Optional[ Mapping[str, Any]],
    high_value_pains: Sequence[Mapping[str, Any]],
    sample_posts_db: Sequence[Mapping[str, Any]],
    sample_comments_db: Sequence[Mapping[str, Any]],
    top_drivers:Optional[ Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    evidence_map: dict[str, dict[str, Any]] = {}

    for post in sample_posts_db:
        pid = str(post.get("id") or "").strip()
        if not pid:
            continue
        evidence_map[pid] = {
            "id": pid,
            "type": "post",
            "text": post.get("text") or post.get("summary") or post.get("title") or "",
            "url": post.get("permalink") or post.get("url") or "",
            "subreddit": post.get("subreddit") or "",
        }
    for comment in sample_comments_db:
        cid = str(comment.get("id") or "").strip()
        if not cid:
            continue
        evidence_map[cid] = {
            "id": cid,
            "type": "comment",
            "text": comment.get("text") or comment.get("body") or "",
            "url": comment.get("permalink") or "",
            "subreddit": comment.get("subreddit") or "",
        }

    pains_payload: list[dict[str, Any]] = []
    for pain in high_value_pains:
        name = str(pain.get("name") or pain.get("description") or "").strip()
        evidence_ids = [str(x) for x in (pain.get("evidence_quote_ids") or []) if x]
        pains_payload.append(
            {
                "name": name,
                "mentions": int(pain.get("mentions") or 0),
                "unique_authors": int(pain.get("unique_authors") or 0),
                "evidence_ids": evidence_ids,
                "evidence": [evidence_map[eid] for eid in evidence_ids if eid in evidence_map],
            }
        )

    drivers_payload: list[dict[str, Any]] = []
    for driver in top_drivers or []:
        drivers_payload.append(
            {
                "title": driver.get("title") or "",
                "description": driver.get("description") or driver.get("rationale") or "",
                "actions": driver.get("actions") or [],
                "source_pains": driver.get("source_pains") or [],
            }
        )

    communities_payload = []
    if aggregates and isinstance(aggregates, Mapping):
        communities_payload = list(aggregates.get("communities") or [])

    return {
        "communities": communities_payload,
        "pain_points": pains_payload,
        "drivers": drivers_payload,
        "evidence": list(evidence_map.values()),
    }


def build_analysis_output_artifacts(
    *,
    facts_v2_package:Optional[ dict[str, Any]],
    facts_v2_quality:Optional[ Mapping[str, Any]],
    insights:Optional[ Mapping[str, Any]],
    ps_ratio_value:Optional[ float],
    aggregates:Optional[ Mapping[str, Any]],
    high_value_pains: Sequence[Mapping[str, Any]],
    sample_posts_db: Sequence[Mapping[str, Any]],
    sample_comments_db: Sequence[Mapping[str, Any]],
    build_evidence_ledger_fn: Callable[..., dict[str, Any]],
    build_facts_slice_for_report_fn: Callable[..., dict[str, Any]],
) -> AnalysisOutputArtifacts:
    if facts_v2_package is None:
        return AnalysisOutputArtifacts(
            evidence_ledger=None,
            facts_slice=None,
            knowledge_graph=None,
        )

    insights_map = dict(insights or {})
    evidence_ledger = build_evidence_ledger_fn(
        insights=insights_map,
        sample_posts_db=sample_posts_db,
        sample_comments_db=sample_comments_db,
    )
    facts_v2_package["evidence_ledger"] = evidence_ledger

    facts_slice = build_facts_slice_for_report_fn(
        facts_v2_package=facts_v2_package,
        facts_v2_quality=facts_v2_quality if isinstance(facts_v2_quality, Mapping) else None,
        trend_summary=insights_map.get("trend_summary"),
        market_saturation=insights_map.get("market_saturation"),
        battlefield_profiles=insights_map.get("battlefield_profiles"),
        top_drivers=insights_map.get("top_drivers"),
    )
    if ps_ratio_value is not None:
        facts_slice["ps_ratio"] = round(ps_ratio_value, 2)

    knowledge_graph = build_knowledge_graph(
        aggregates=aggregates,
        high_value_pains=high_value_pains,
        sample_posts_db=sample_posts_db,
        sample_comments_db=sample_comments_db,
        top_drivers=insights_map.get("top_drivers"),
    )
    facts_slice["knowledge_graph"] = knowledge_graph

    return AnalysisOutputArtifacts(
        evidence_ledger=evidence_ledger,
        facts_slice=facts_slice,
        knowledge_graph=knowledge_graph,
    )
