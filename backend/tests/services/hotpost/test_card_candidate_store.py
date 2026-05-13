from __future__ import annotations

from datetime import datetime, timezone


def _candidate(candidate_id: str) -> dict:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "candidate_id": candidate_id,
        "signal_id": f"sig-{candidate_id}",
        "source_scope_id": "business-growth-ops",
        "source_scope_name": "商业增长与运营",
        "topic_pack_id": "paid-economics",
        "topic_cluster_id": "ads",
        "topic_cluster_ids": ["ads"],
        "named_topic_ids": [],
        "query": "meta ads",
        "matched_subreddit": "FacebookAds",
        "post_id": candidate_id.replace("cand-", ""),
        "title": f"title-{candidate_id}",
        "score": 10,
        "num_comments": 5,
        "created_at": now,
        "collected_at": now,
        "collect_batch_id": "batch-1",
        "time_window": "24h",
        "signal_level": "sustained",
        "why_now_reason": "new_threads_24h",
        "listing_source": "listing:hot:day",
        "primary_reason": "paid-economics:listing_hot",
        "matched_keywords": [],
        "top_communities": ["r/FacebookAds"],
        "thread_count": 1,
        "community_count": 1,
        "quote_count": 0,
        "intent_tags": ["趋势变化"],
        "evidence_quotes": [],
    }


def test_list_candidates_hides_rejected_by_default(monkeypatch) -> None:
    from app.services.hotpost import card_candidate_store as mod

    candidates = [_candidate("cand-keep"), _candidate("cand-rejected")]
    monkeypatch.setattr(mod, "load_candidates", lambda: candidates)
    monkeypatch.setattr(mod, "list_rejected_candidate_ids", lambda: {"cand-rejected"})

    items = mod.list_candidates()

    assert [item.candidate_id for item in items] == ["cand-keep"]


def test_list_candidates_can_include_rejected_when_requested(monkeypatch) -> None:
    from app.services.hotpost import card_candidate_store as mod

    candidates = [_candidate("cand-keep"), _candidate("cand-rejected")]
    monkeypatch.setattr(mod, "load_candidates", lambda: candidates)
    monkeypatch.setattr(mod, "list_rejected_candidate_ids", lambda: {"cand-rejected"})

    items = mod.list_candidates(include_rejected=True)

    assert {item.candidate_id for item in items} == {"cand-keep", "cand-rejected"}
