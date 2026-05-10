from __future__ import annotations

from app.services.hotpost.hot_lane_eval_set_builder import build_hot_lane_eval_artifacts


def _published(card_id: str, *, lane: str, scope_id: str, listing: str = "listing:top:day") -> dict:
    return {
        "card_id": card_id,
        "signal_id": f"sig-{card_id}",
        "card_type": "validate",
        "lane": lane,
        "source_scope_id": scope_id,
        "source_scope_name": scope_id,
        "topic_pack_id": "upstream-winds",
        "signal_level": "hot",
        "why_now_reason": "new_threads_24h",
        "intent_tags": ["趋势变化"],
        "title": "title",
        "summary_line": "summary",
        "audience": "audience",
        "why_now": "why now",
        "detail": {"pain_point": "a", "target_user_and_scene": "b", "why_test_now": "c", "min_test_action": "x", "continue_signal": "d", "stop_signal": "e"},
        "listing_source": listing,
        "source_module": {"primary_communities": ["r/artificial"], "top_community": "r/artificial", "thread_count": 1, "community_count": 1, "last_active_text": "近24小时", "tone_tags": []},
        "preview_quote": {"text": "quote", "community": "r/artificial", "permalink": "https://reddit.com/q"},
        "quotes": [{"text": "quote", "community": "r/artificial", "permalink": "https://reddit.com/q"}],
    }


def _candidate(candidate_id: str, *, scope_id: str, listing: str = "listing:top:day") -> dict:
    return {
        "candidate_id": candidate_id,
        "signal_id": f"sig-{candidate_id}",
        "source_scope_id": scope_id,
        "source_scope_name": scope_id,
        "topic_pack_id": "category-winds",
        "title": "candidate title",
        "signal_level": "rising",
        "listing_source": listing,
        "thread_count": 1,
        "community_count": 1,
        "quote_count": 2,
        "intent_tags": ["趋势变化"],
        "top_communities": ["r/ecommerce"],
        "evidence_quotes": [{"text": "real quote with enough context to keep", "community": "r/ecommerce", "permalink": "https://reddit.com/c"}],
    }


def test_build_hot_lane_eval_artifacts_mixes_hot_signal_and_candidates(monkeypatch) -> None:
    from app.services.hotpost import hot_lane_eval_set_builder as mod

    monkeypatch.setattr(
        mod,
        "load_cards_payload",
        lambda: {
            "published": [
                _published("hot-1", lane="hot", scope_id="ai-automation"),
                _published("sig-1", lane="signal", scope_id="business-growth-ops"),
            ],
            "candidates": [_candidate("cand-1", scope_id="ecommerce-sellers")],
        },
    )
    artifacts = build_hot_lane_eval_artifacts(target_real=3)
    assert len(artifacts["real_cases"]) == 3
    assert [item["sample_origin"] for item in artifacts["real_cases"]] == [
        "published_hot",
        "candidate_listing_unpublished",
        "published_listing_signal",
    ]
    assert len(artifacts["labels"]) == 3
    assert artifacts["labels"][0]["lane_decision"] is None
    assert artifacts["manifest"]["real_count"] == 3
