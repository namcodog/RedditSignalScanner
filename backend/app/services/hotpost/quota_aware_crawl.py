from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_source_scopes import RedditSearchSpec
from app.services.hotpost.card_candidate_store import list_candidates
from app.services.hotpost.card_lane_policy import infer_validation_lane
from app.services.hotpost.hotpost_priority_targets import PUBLISH_PRIORITY_CLUSTER_IDS


DRY_CYCLE_DEFAULT = 3
QUOTA_AWARE_CRAWL_WINNER = "discover_first_comment_late_adaptive_pacing_sociavault_assist_v3"
DISCOVER_PHASE = "discover"
ENRICH_PHASE = "enrich"
BACKFILL_PHASE = "backfill"
CRAWL_PHASE_ORDER = (DISCOVER_PHASE, ENRICH_PHASE, BACKFILL_PHASE)


def split_specs_for_crawl(specs: list[RedditSearchSpec]) -> dict[str, list[RedditSearchSpec]]:
    discover_specs: list[RedditSearchSpec] = []
    backfill_specs: list[RedditSearchSpec] = []
    for spec in specs:
        if _is_discover_spec(spec):
            discover_specs.append(spec)
        else:
            backfill_specs.append(spec)
    return {
        DISCOVER_PHASE: discover_specs,
        BACKFILL_PHASE: backfill_specs,
    }


def build_enrich_shortlist(candidates: list[CandidatePack], *, max_items: int) -> list[CandidatePack]:
    ranked = sorted(
        [
            candidate
            for candidate in candidates
            if infer_validation_lane(candidate) in {"hot", "signal"}
        ],
        key=lambda item: (
            0 if infer_validation_lane(item) == "hot" else 1,
            -item.score,
            -item.num_comments,
            -item.created_at.timestamp(),
        ),
    )
    base_limit = max(1, max_items)
    base = ranked[:base_limit]
    base_ids = {candidate.candidate_id for candidate in base}
    extras: list[CandidatePack] = []
    extra_ids: set[str] = set()
    for cluster_id in PUBLISH_PRIORITY_CLUSTER_IDS:
        taken_for_cluster = 0
        for candidate in ranked:
            if candidate.candidate_id in base_ids or candidate.candidate_id in extra_ids:
                continue
            if not _candidate_has_cluster(candidate, cluster_id):
                continue
            extras.append(candidate)
            extra_ids.add(candidate.candidate_id)
            taken_for_cluster += 1
            if taken_for_cluster >= 2 or len(extras) >= 4:
                break
        if len(extras) >= 4:
            break
    return [*base, *extras]


def measure_publishable_gain(*, source_scope_id: str | None = None) -> dict[str, int]:
    reference_time = datetime.now(timezone.utc)
    counts: Counter[str] = Counter()
    for candidate in list_candidates(source_scope_id=source_scope_id):
        lane = infer_validation_lane(candidate)
        age_hours = (reference_time - candidate.created_at).total_seconds() / 3600.0
        counts[f"{lane}_total"] += 1
        if lane == "hot" and age_hours <= 24.0:
            counts["hot_target_fresh"] += 1
        elif lane == "signal" and age_hours <= 72.0:
            counts["signal_target_fresh"] += 1
        elif lane == "breakdown" and age_hours <= 24.0 * 10.0:
            counts["breakdown_acceptable_fresh"] += 1
    counts["publishable_total"] = (
        counts["hot_target_fresh"]
        + counts["signal_target_fresh"]
        + counts["breakdown_acceptable_fresh"]
    )
    return dict(counts)


def has_publishable_gain(previous: dict[str, int], current: dict[str, int]) -> bool:
    return int(current.get("publishable_total") or 0) > int(previous.get("publishable_total") or 0)


def _is_discover_spec(spec: RedditSearchSpec) -> bool:
    if spec.mode == "listing":
        return spec.time_filter == "day" and spec.sort in {"hot", "new", "rising"}
    return spec.time_filter == "day"


def _candidate_has_cluster(candidate: CandidatePack, cluster_id: str) -> bool:
    clusters = {item for item in candidate.topic_cluster_ids if item}
    if candidate.topic_cluster_id:
        clusters.add(candidate.topic_cluster_id)
    return cluster_id in clusters


__all__ = [
    "BACKFILL_PHASE",
    "CRAWL_PHASE_ORDER",
    "DISCOVER_PHASE",
    "DRY_CYCLE_DEFAULT",
    "ENRICH_PHASE",
    "QUOTA_AWARE_CRAWL_WINNER",
    "build_enrich_shortlist",
    "has_publishable_gain",
    "measure_publishable_gain",
    "split_specs_for_crawl",
]
