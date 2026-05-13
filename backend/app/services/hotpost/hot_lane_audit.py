from __future__ import annotations

from collections import Counter

from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.card_candidate_store import list_candidates
from app.services.hotpost.card_lane_policy import infer_validation_lane
from app.services.hotpost.card_payload_store import load_published_cards


def build_hot_lane_audit() -> dict:
    candidates = [item for scope in ("ai-automation", "business-growth-ops", "ecommerce-sellers") for item in list_candidates(scope)]
    listing = [item for item in candidates if item.listing_source.startswith("listing:")]
    runtime_hot = [item for item in candidates if infer_validation_lane(item) == "hot"]
    listing_hot = [item for item in runtime_hot if item.listing_source.startswith("listing:")]
    search_hot = [item for item in runtime_hot if not item.listing_source.startswith("listing:")]
    runtime_signal = [item for item in listing if infer_validation_lane(item) == "signal"]
    published = load_published_cards()
    published_hot = [item for item in published if item.get("lane") == "hot"]
    published_signal_ids = {str(item.get("signal_id")).strip() for item in published if str(item.get("signal_id") or "").strip()}
    runtime_hot_unpublished = [item for item in runtime_hot if item.signal_id not in published_signal_ids]
    runtime_hot_published = [item for item in runtime_hot if item.signal_id in published_signal_ids]
    return {
        "candidate_total": len(candidates),
        "listing_total": len(listing),
        "runtime_hot_total": len(runtime_hot),
        "runtime_hot_unpublished_total": len(runtime_hot_unpublished),
        "runtime_hot_published_total": len(runtime_hot_published),
        "runtime_hot_listing_total": len(listing_hot),
        "runtime_hot_search_total": len(search_hot),
        "runtime_signal_listing_total": len(runtime_signal),
        "published_hot_total": len(published_hot),
        "runtime_hot_by_scope": dict(Counter(item.source_scope_id for item in runtime_hot)),
        "runtime_hot_unpublished_by_scope": dict(Counter(item.source_scope_id for item in runtime_hot_unpublished)),
        "runtime_hot_by_pack": dict(Counter(item.topic_pack_id for item in runtime_hot)),
        "runtime_hot_by_subreddit": dict(Counter(item.matched_subreddit for item in runtime_hot)),
        "published_hot_by_scope": dict(Counter(item["source_scope_id"] for item in published_hot)),
        "runtime_hot_candidates": [
            _pack_summary(item) for item in sorted(runtime_hot_unpublished, key=lambda x: (x.num_comments, x.score), reverse=True)
        ],
        "runtime_hot_published_candidates": [
            _pack_summary(item) for item in sorted(runtime_hot_published, key=lambda x: (x.num_comments, x.score), reverse=True)
        ],
        "top_listing_signal_candidates": [_pack_summary(item) for item in sorted(runtime_signal, key=lambda x: (x.num_comments, x.score), reverse=True)[:12]],
    }


def _pack_summary(candidate: CandidatePack) -> dict:
    return {
        "candidate_id": candidate.candidate_id,
        "scope_id": candidate.source_scope_id,
        "topic_pack_id": candidate.topic_pack_id,
        "subreddit": candidate.matched_subreddit,
        "score": candidate.score,
        "num_comments": candidate.num_comments,
        "signal_level": candidate.signal_level,
        "listing_source": candidate.listing_source,
        "title": candidate.title,
    }


__all__ = ["build_hot_lane_audit"]
