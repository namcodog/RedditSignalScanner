from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.intake_freshness_gate import LANE_WINDOWS_HOURS


THIN_PACK_IDS = {
    "upstream-winds",
    "tools-efficiency",
    "funnel-conversion",
    "category-winds",
}

EXPLORATION_CLUSTER_IDS = {
    "key-people-and-route",
    "ai-product-and-adoption",
    "platform-policy-shifts",
    "small-goods",
}

HARD_REJECT_REASONS = {
    "no_substantive_quotes",
    "complaint_only_no_market_signal",
    "meta_community_complaint",
    "joke_or_satire_low_signal",
    "low_information_density",
    "why_now_unclear",
    "exploration_requires_two_quotes",
    "obviously_stale",
}

RELAXABLE_REASONS = {
    "single_thread_weak_evidence",
    "single_community_weak_evidence",
}


def assess_tiered_publish_surface_candidate(
    candidate: CandidatePack,
    *,
    lane: str,
    base_quality: dict[str, Any],
) -> dict[str, Any]:
    tier = _resolve_surface_tier(candidate)
    base_reasons = [str(reason) for reason in list(base_quality.get("reasons") or [])]
    blocking_reasons = list(base_reasons)
    blocking_reasons.extend(_surface_contract_reasons(candidate))
    relaxed_reasons: list[str] = []
    freshness_reason = _freshness_reason(candidate, lane=lane, tier=tier)
    if freshness_reason:
        blocking_reasons.append(freshness_reason)

    if tier == "exploration":
        extra_reasons = _exploration_contract_reasons(candidate, base_quality=base_quality)
        blocking_reasons.extend(extra_reasons)
        hard_reasons = [reason for reason in blocking_reasons if reason in HARD_REJECT_REASONS]
        if hard_reasons:
            return {
                "tier": tier,
                "should_block": True,
                "reasons": _dedupe(blocking_reasons),
                "base_reasons": base_reasons,
                "relaxed_reasons": relaxed_reasons,
            }
        relaxed_reasons = [reason for reason in blocking_reasons if reason in RELAXABLE_REASONS]
        final_reasons = [
            reason
            for reason in blocking_reasons
            if reason not in RELAXABLE_REASONS and reason != "exploration_freshness_relax"
        ]
        return {
            "tier": tier,
            "should_block": bool(final_reasons),
            "reasons": _dedupe(final_reasons),
            "base_reasons": base_reasons,
            "relaxed_reasons": _dedupe(relaxed_reasons),
        }

    return {
        "tier": tier,
        "should_block": bool(blocking_reasons),
        "reasons": _dedupe(blocking_reasons),
        "base_reasons": base_reasons,
        "relaxed_reasons": relaxed_reasons,
    }


def _resolve_surface_tier(candidate: CandidatePack) -> str:
    if str(candidate.topic_pack_id or "") in THIN_PACK_IDS:
        return "exploration"
    cluster_ids = {str(item).strip() for item in (candidate.topic_cluster_ids or []) if str(item).strip()}
    if str(candidate.topic_cluster_id or "").strip():
        cluster_ids.add(str(candidate.topic_cluster_id).strip())
    if cluster_ids & EXPLORATION_CLUSTER_IDS:
        return "exploration"
    return "strong"


def _exploration_contract_reasons(
    candidate: CandidatePack,
    *,
    base_quality: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if int(base_quality.get("substantive_quote_count") or 0) < 2:
        reasons.append("exploration_requires_two_quotes")
    if not str(candidate.why_now_reason or "").strip():
        reasons.append("why_now_unclear")
    if not _has_enough_information_density(candidate):
        reasons.append("low_information_density")
    return reasons


def _surface_contract_reasons(candidate: CandidatePack) -> list[str]:
    reasons: list[str] = []
    if int(candidate.thread_count or 0) <= 1:
        reasons.append("single_thread_weak_evidence")
    if int(candidate.community_count or 0) <= 1:
        reasons.append("single_community_weak_evidence")
    return reasons


def _has_enough_information_density(candidate: CandidatePack) -> bool:
    quote_texts = [str((quote or {}).text if hasattr(quote, "text") else (quote or {}).get("text") or "").strip() for quote in candidate.evidence_quotes]
    nonempty = [text for text in quote_texts if text]
    if len(nonempty) < 2:
        return False
    total_chars = sum(len(text) for text in nonempty)
    long_quote = any(len(text) >= 72 for text in nonempty)
    return total_chars >= 140 or long_quote


def _freshness_reason(candidate: CandidatePack, *, lane: str, tier: str) -> str | None:
    windows = LANE_WINDOWS_HOURS.get(lane)
    if not windows:
        return None
    event_at = candidate.created_at
    age_hours = max((datetime.now(timezone.utc) - event_at).total_seconds() / 3600.0, 0.0)
    if age_hours > float(windows["max"]):
        return "obviously_stale"
    if tier == "strong" and age_hours > float(windows["target"]):
        return "strong_lane_stale"
    return None


def _dedupe(reasons: list[str]) -> list[str]:
    return list(dict.fromkeys(reason for reason in reasons if reason))


__all__ = [
    "EXPLORATION_CLUSTER_IDS",
    "HARD_REJECT_REASONS",
    "RELAXABLE_REASONS",
    "THIN_PACK_IDS",
    "assess_tiered_publish_surface_candidate",
]
