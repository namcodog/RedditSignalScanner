from __future__ import annotations

from collections import Counter

from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.card_lane_policy import infer_validation_lane, resolve_lane
from app.services.hotpost.hotpost_supply_contract import get_supply_rolling_publish_mix


def _recent_window(published_items: list[dict]) -> list[dict]:
    rules = get_supply_rolling_publish_mix()
    window_size = int(rules["window_size"])
    ordered = sorted(
        published_items,
        key=lambda item: str(item.get("published_at") or item.get("updated_at") or item.get("created_at") or ""),
    )
    return ordered[-window_size:]


def build_scope_mix_snapshot(published_items: list[dict]) -> dict[str, int]:
    rules = get_supply_rolling_publish_mix()
    recent_items = _recent_window(published_items)
    scope_counts = Counter(str(item.get("source_scope_id") or "") for item in recent_items)
    return {scope_id: int(scope_counts.get(scope_id, 0)) for scope_id in rules["scope_targets"]}


def build_lane_mix_snapshot(published_items: list[dict]) -> dict[str, int]:
    rules = get_supply_rolling_publish_mix()
    recent_items = _recent_window(published_items)
    lane_counts = Counter(resolve_lane(item.get("lane"), card_type=str(item.get("card_type") or "validate")) for item in recent_items)
    return {lane: int(lane_counts.get(lane, 0)) for lane in rules["lane_targets"]}


def score_validate_candidate(
    candidate: CandidatePack,
    *,
    recent_scope_mix: dict[str, int],
    recent_lane_mix: dict[str, int],
) -> tuple[float, list[str]]:
    rules = get_supply_rolling_publish_mix()
    score = 0.0
    reasons: list[str] = []

    lane = infer_validation_lane(candidate)
    lane_target = int(rules["lane_targets"].get(lane, 0))
    lane_current = int(recent_lane_mix.get(lane, 0))
    lane_gap = lane_target - lane_current
    if lane_gap > 0:
        score += lane_gap * 14.0
        reasons.append(f"lane_gap:{lane_gap}")
    elif lane == "signal" and lane_current >= lane_target:
        score -= (lane_current - lane_target + 1) * 8.0
        reasons.append("signal_over_target")
    if lane == "hot":
        score += 28.0
        reasons.append("hot_lane")

    scope_target = int(rules["scope_targets"].get(candidate.source_scope_id, 0))
    scope_current = int(recent_scope_mix.get(candidate.source_scope_id, 0))
    scope_gap = scope_target - scope_current
    if scope_gap > 0:
        score += scope_gap * 10.0
        reasons.append(f"scope_gap:{scope_gap}")
    elif scope_gap < 0:
        score += scope_gap * 4.0
        reasons.append("scope_over_target")

    if candidate.listing_source.startswith("listing:"):
        score += 8.0
        reasons.append("listing_first")

    score += min(candidate.num_comments / 25.0, 8.0)
    score += min(candidate.score / 100.0, 5.0)
    return score, reasons


def prioritize_validate_candidates(
    candidates: list[CandidatePack],
    *,
    published_items: list[dict],
) -> list[CandidatePack]:
    scope_mix = build_scope_mix_snapshot(published_items)
    lane_mix = build_lane_mix_snapshot(published_items)
    ranked = []
    for index, candidate in enumerate(candidates):
        score, _ = score_validate_candidate(
            candidate,
            recent_scope_mix=scope_mix,
            recent_lane_mix=lane_mix,
        )
        ranked.append((-score, index, candidate))
    ranked.sort()
    return [candidate for _, _, candidate in ranked]


__all__ = [
    "build_lane_mix_snapshot",
    "build_scope_mix_snapshot",
    "prioritize_validate_candidates",
    "score_validate_candidate",
]
