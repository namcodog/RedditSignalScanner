from __future__ import annotations

from typing import Any

from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.card_lane_policy import infer_validation_lane
from app.services.hotpost.publish_surface_gate_tiering import assess_tiered_publish_surface_candidate
from app.services.hotpost.signal_input_quality import assess_signal_input_quality


def assess_publish_surface_candidate(
    candidate: CandidatePack,
    *,
    lane: str | None = None,
) -> dict[str, Any]:
    resolved_lane = lane or infer_validation_lane(candidate)
    base_quality = assess_signal_input_quality(candidate.model_dump(mode="json"))
    tiered_quality = assess_tiered_publish_surface_candidate(
        candidate,
        lane=resolved_lane,
        base_quality=base_quality,
    )
    return {
        "lane": resolved_lane,
        **tiered_quality,
    }


def should_keep_publish_surface_candidate(
    candidate: CandidatePack,
    *,
    lane: str | None = None,
) -> bool:
    return not assess_publish_surface_candidate(candidate, lane=lane)["should_block"]


__all__ = [
    "assess_publish_surface_candidate",
    "should_keep_publish_surface_candidate",
]
