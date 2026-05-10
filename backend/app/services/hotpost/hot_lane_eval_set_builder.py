from __future__ import annotations

from collections import Counter
from typing import Any

from app.services.hotpost.card_lane_policy import resolve_lane
from app.services.hotpost.card_payload_store import load_candidates, load_published_cards
from app.services.hotpost.signal_input_quality import assess_signal_input_quality


HOT_LANE_FAILURE_TAGS = [
    "meta_community_complaint",
    "pure_emotional_venting",
    "ideological_argument",
    "no_clear_debate_focus",
    "actually_signal_not_hot",
    "meme_or_low_information",
]
_ORIGIN_PRIORITY = {"published_hot": 0, "candidate_listing_unpublished": 1, "published_listing_signal": 2}


def build_hot_lane_eval_artifacts(*, target_real: int = 18) -> dict[str, Any]:
    published = load_published_cards()
    candidates = load_candidates()
    published_signal_ids = {item["signal_id"] for item in published if item.get("signal_id")}
    real_cases = [_published_case(item) for item in published if _is_hot_card(item)]
    real_cases.extend(_candidate_case(item) for item in candidates if _is_hot_candidate(item, published_signal_ids))
    real_cases.extend(_published_case(item) for item in published if _is_listing_signal(item))
    selected = _select_cases(real_cases, target_real)
    labels = [_empty_label(item["eval_case_id"]) for item in selected]
    manifest = {
        "target_real": target_real,
        "real_count": len(selected),
        "origin_counts": dict(Counter(item["sample_origin"] for item in selected)),
        "source_scope_counts": dict(Counter(item["input_bundle"]["source_scope_id"] for item in selected)),
    }
    return {"real_cases": selected, "labels": labels, "manifest": manifest}


def _published_case(item: dict[str, Any]) -> dict[str, Any]:
    source = item["source_module"]
    lane = resolve_lane(item.get("lane"), card_type=item["card_type"])
    return {
        "eval_case_id": f"hot-lane-eval-published-{item['card_id']}",
        "sample_origin": "published_hot" if lane == "hot" else "published_listing_signal",
        "input_bundle": {
            "source_scope_id": item["source_scope_id"],
            "source_scope_name": item["source_scope_name"],
            "topic_pack_id": item.get("topic_pack_id"),
            "signal_level": item.get("signal_level"),
            "listing_source": item.get("listing_source"),
            "intent_tags": item.get("intent_tags") or [],
            "thread_count": source["thread_count"],
            "community_count": source["community_count"],
            "quote_count": len(item.get("quotes") or []),
            "source_communities": source["primary_communities"],
            "evidence_quotes": item.get("quotes") or [item["preview_quote"]],
            "input_quality": assess_signal_input_quality(
                {
                    "title": item["title"],
                    "thread_count": source["thread_count"],
                    "community_count": source["community_count"],
                    "intent_tags": item.get("intent_tags") or [],
                    "evidence_quotes": item.get("quotes") or [item["preview_quote"]],
                }
            ),
        },
        "baseline_output": {key: item[key] for key in ("title", "summary_line", "audience", "why_now", "detail")},
        "metadata": {"card_id": item["card_id"], "current_lane": lane},
    }


def _candidate_case(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "eval_case_id": f"hot-lane-eval-candidate-{item['candidate_id']}",
        "sample_origin": "candidate_listing_unpublished",
        "input_bundle": {
            "source_scope_id": item["source_scope_id"],
            "source_scope_name": item["source_scope_name"],
            "topic_pack_id": item.get("topic_pack_id"),
            "signal_level": item.get("signal_level"),
            "listing_source": item.get("listing_source"),
            "intent_tags": item.get("intent_tags") or [],
            "thread_count": item.get("thread_count") or 0,
            "community_count": item.get("community_count") or 0,
            "quote_count": item.get("quote_count") or 0,
            "source_communities": item.get("top_communities") or [],
            "evidence_quotes": item.get("evidence_quotes") or [],
            "input_quality": assess_signal_input_quality(item),
        },
        "baseline_output": None,
        "metadata": {"candidate_id": item["candidate_id"]},
    }


def _select_cases(cases: list[dict[str, Any]], needed: int) -> list[dict[str, Any]]:
    picked: list[dict[str, Any]] = []
    scope_counts: Counter[str] = Counter()
    seen: set[str] = set()
    for item in sorted(cases, key=_case_sort_key):
        if len(picked) >= needed:
            break
        signature = item["metadata"].get("card_id") or item["metadata"].get("candidate_id")
        if signature in seen:
            continue
        scope_id = item["input_bundle"]["source_scope_id"]
        if scope_counts[scope_id] > min(scope_counts.values(), default=0) + 1:
            continue
        picked.append(item)
        seen.add(signature)
        scope_counts[scope_id] += 1
    return picked


def _case_sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    quality = item["input_bundle"]["input_quality"]
    quality_rank = 0 if not quality["should_block"] else 1
    engagement = -(item["input_bundle"]["quote_count"] + item["input_bundle"]["thread_count"] + item["input_bundle"]["community_count"])
    return (_ORIGIN_PRIORITY[item["sample_origin"]], quality_rank, engagement, item["eval_case_id"])


def _is_hot_card(item: dict[str, Any]) -> bool:
    return item.get("card_type") == "validate" and resolve_lane(item.get("lane"), card_type=item["card_type"]) == "hot"


def _is_listing_signal(item: dict[str, Any]) -> bool:
    return item.get("card_type") == "validate" and resolve_lane(item.get("lane"), card_type=item["card_type"]) == "signal" and str(item.get("listing_source") or "").startswith("listing:")


def _is_hot_candidate(item: dict[str, Any], published_signal_ids: set[str]) -> bool:
    return item.get("signal_id") not in published_signal_ids and str(item.get("listing_source") or "").startswith("listing:")


def _empty_label(eval_case_id: str) -> dict[str, Any]:
    return {
        "eval_case_id": eval_case_id,
        "lane_decision": None,
        "failure_tags": [],
        "review_notes": "",
        "review_status": "pending",
    }


__all__ = ["HOT_LANE_FAILURE_TAGS", "build_hot_lane_eval_artifacts"]
