from __future__ import annotations

from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.hot_lane_audit import build_hot_lane_audit


def _candidate(candidate_id: str, signal_id: str, *, score: int, num_comments: int) -> CandidatePack:
    return CandidatePack.model_validate(
        {
            "candidate_id": candidate_id,
            "signal_id": signal_id,
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "topic_pack_id": "upstream-winds",
            "query": "listing:hot:day",
            "matched_subreddit": "OpenAI",
            "post_id": f"post-{candidate_id}",
            "title": f"title-{candidate_id}",
            "score": score,
            "num_comments": num_comments,
            "created_at": "2026-04-10T00:00:00Z",
            "collected_at": "2026-04-10T00:00:00Z",
            "collect_batch_id": "batch-1",
            "time_window": "24h",
            "signal_level": "hot",
            "why_now_reason": "new_threads_24h",
            "listing_source": "listing:hot:day",
            "primary_reason": "upstream-winds:listing_hot",
            "matched_keywords": [],
            "top_communities": ["r/OpenAI"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 2,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [
                {"text": "People are arguing now.", "community": "r/OpenAI", "permalink": "https://reddit.com/1"},
                {"text": "The thread is clearly heated.", "community": "r/OpenAI", "permalink": "https://reddit.com/2"},
            ],
        }
    )


def test_build_hot_lane_audit_splits_unpublished_from_already_published(monkeypatch) -> None:
    from app.services.hotpost import hot_lane_audit as mod

    published_hot = _candidate("cand-hot-published", "sig-hot-published", score=420, num_comments=91)
    fresh_hot = _candidate("cand-hot-fresh", "sig-hot-fresh", score=310, num_comments=64)
    signal_candidate = _candidate("cand-signal", "sig-signal", score=18, num_comments=9)

    def _list_candidates(source_scope_id: str) -> list[CandidatePack]:
        if source_scope_id == "ai-automation":
            return [published_hot, fresh_hot, signal_candidate]
        return []

    monkeypatch.setattr(mod, "list_candidates", _list_candidates)
    monkeypatch.setattr(
        mod,
        "infer_validation_lane",
        lambda item: "hot" if item.candidate_id in {"cand-hot-published", "cand-hot-fresh"} else "signal",
    )
    monkeypatch.setattr(
        mod,
        "load_published_cards",
        lambda: [{"signal_id": "sig-hot-published", "lane": "hot", "source_scope_id": "ai-automation"}],
    )

    audit = build_hot_lane_audit()

    assert audit["runtime_hot_total"] == 2
    assert audit["runtime_hot_unpublished_total"] == 1
    assert audit["runtime_hot_published_total"] == 1
    assert [item["candidate_id"] for item in audit["runtime_hot_candidates"]] == ["cand-hot-fresh"]
    assert [item["candidate_id"] for item in audit["runtime_hot_published_candidates"]] == ["cand-hot-published"]
