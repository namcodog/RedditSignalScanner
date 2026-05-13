from __future__ import annotations

from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.card_selection_policy import (
    build_lane_mix_snapshot,
    build_scope_mix_snapshot,
    prioritize_validate_candidates,
    score_validate_candidate,
)


def _candidate(
    candidate_id: str,
    source_scope_id: str,
    listing_source: str,
    score: int,
    comments: int,
    *,
    title: str = "How are you getting through this downturn?",
    intent_tags: list[str] | None = None,
    evidence_quotes: list[dict[str, str]] | None = None,
) -> CandidatePack:
    topic_pack_map = {
        "ai-automation": "upstream-winds",
        "business-growth-ops": "organic-discovery",
        "ecommerce-sellers": "selection-signals",
    }
    return CandidatePack.model_validate(
        {
            "candidate_id": candidate_id,
            "signal_id": f"sig-{candidate_id}",
            "source_scope_id": source_scope_id,
            "source_scope_name": "scope",
            "topic_pack_id": topic_pack_map[source_scope_id],
            "query": "q",
            "matched_subreddit": "sub",
            "post_id": "post",
            "title": title,
            "score": score,
            "num_comments": comments,
            "created_at": "2026-04-09T00:00:00Z",
            "collected_at": "2026-04-09T00:00:00Z",
            "collect_batch_id": "batch",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "switch_signal_7d",
            "listing_source": listing_source,
            "primary_reason": "reason",
            "matched_keywords": [],
            "top_communities": ["r/test"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 2,
            "intent_tags": intent_tags or ["趋势变化"],
            "evidence_quotes": evidence_quotes
            or [
                {"text": "After 8 years I'm cooked.", "community": "r/test", "permalink": "https://reddit.com/1"},
                {"text": "I am at 40% lower than last year.", "community": "r/test", "permalink": "https://reddit.com/2"},
            ],
        }
    )


def test_build_mix_snapshots_handle_empty() -> None:
    scope_mix = build_scope_mix_snapshot([])
    lane_mix = build_lane_mix_snapshot([])
    assert scope_mix["ecommerce-sellers"] == 0
    assert lane_mix["hot"] == 0


def test_build_mix_snapshots_use_latest_published_window_not_file_order() -> None:
    published_items = [
        {
            "source_scope_id": "ai-automation",
            "lane": "signal",
            "card_type": "validate",
            "published_at": "2026-04-01T00:00:00Z",
        }
    ] * 18 + [
        {
            "source_scope_id": "business-growth-ops",
            "lane": "hot",
            "card_type": "validate",
            "published_at": "2026-04-09T09:00:00Z",
        },
        {
            "source_scope_id": "ecommerce-sellers",
            "lane": "breakdown",
            "card_type": "write",
            "published_at": "2026-04-09T10:00:00Z",
        },
    ]
    shuffled = list(reversed(published_items))

    scope_mix = build_scope_mix_snapshot(shuffled)
    lane_mix = build_lane_mix_snapshot(shuffled)

    assert lane_mix["hot"] == 1
    assert lane_mix["breakdown"] == 1
    assert scope_mix["business-growth-ops"] == 1
    assert scope_mix["ecommerce-sellers"] == 1


def test_score_validate_candidate_boosts_underweight_scope_and_hot_lane() -> None:
    candidate = _candidate(
        "cand-1",
        "business-growth-ops",
        "listing:top:week",
        180,
        80,
        title="SEO is over and now we have GEO",
    )
    score, reasons = score_validate_candidate(
        candidate,
        recent_scope_mix={
            "ai-automation": 7,
            "business-growth-ops": 3,
            "ecommerce-sellers": 7,
        },
        recent_lane_mix={
            "signal": 10,
            "hot": 2,
            "breakdown": 4,
        },
    )
    assert score > 50
    assert "hot_lane" in reasons
    assert any(reason.startswith("scope_gap:") for reason in reasons)
    assert any(reason.startswith("lane_gap:") for reason in reasons)


def test_prioritize_validate_candidates_prefers_underweight_scope() -> None:
    published_items = (
        [{"source_scope_id": "ai-automation", "lane": "signal"}] * 7
        + [{"source_scope_id": "business-growth-ops", "lane": "signal"}] * 7
        + [{"source_scope_id": "ecommerce-sellers", "lane": "signal"}] * 3
        + [{"source_scope_id": "ecommerce-sellers", "lane": "breakdown"}] * 3
    )
    items = [
        _candidate(
            "cand-ai",
            "ai-automation",
            "search:relevance:week",
            100,
            10,
            title="AI 写会议纪要还是太像模板",
            intent_tags=["工具体验"],
            evidence_quotes=[
                {"text": "The notes read fine, but I still have to rewrite the action items myself.", "community": "r/test", "permalink": "https://reddit.com/1"},
                {"text": "It saves formatting time, not the actual follow-up work.", "community": "r/test", "permalink": "https://reddit.com/2"},
            ],
        ),
        _candidate(
            "cand-ecom",
            "ecommerce-sellers",
            "listing:top:week",
            50,
            28,
            title="同一批货越卖越难，卖家开始回头算类目是不是已经挤满了",
            intent_tags=["趋势变化"],
            evidence_quotes=[
                {"text": "Margins keep shrinking because everyone is sourcing the same product now.", "community": "r/test", "permalink": "https://reddit.com/1"},
                {"text": "I can still sell it, but the category feels overcrowded compared with last year.", "community": "r/test", "permalink": "https://reddit.com/2"},
            ],
        ),
    ]
    ranked = prioritize_validate_candidates(items, published_items=published_items)
    assert ranked[0].candidate_id == "cand-ecom"


def test_prioritize_validate_candidates_prefers_hot_when_recent_mix_is_short() -> None:
    published_items = (
        [{"source_scope_id": "ai-automation", "lane": "signal"}] * 8
        + [{"source_scope_id": "business-growth-ops", "lane": "signal"}] * 6
        + [{"source_scope_id": "ecommerce-sellers", "lane": "signal"}] * 3
        + [{"source_scope_id": "ai-automation", "lane": "breakdown"}] * 3
    )
    items = [
        _candidate("cand-signal", "business-growth-ops", "search:relevance:week", 120, 22),
        _candidate("cand-hot", "business-growth-ops", "listing:top:week", 180, 80),
    ]
    ranked = prioritize_validate_candidates(items, published_items=published_items)
    assert ranked[0].candidate_id == "cand-hot"


def test_score_validate_candidate_penalizes_signal_when_lane_is_already_over_target() -> None:
    candidate = _candidate(
        "cand-signal",
        "business-growth-ops",
        "search:relevance:week",
        130,
        18,
        title="品牌词被 Google 自动改写后，前期流量可能根本没进来",
        intent_tags=["趋势变化"],
        evidence_quotes=[
            {"text": "We are getting impressions, but almost none of them are turning into branded clicks yet.", "community": "r/test", "permalink": "https://reddit.com/1"},
            {"text": "The page is indexed, but the early traffic is thinner than we expected.", "community": "r/test", "permalink": "https://reddit.com/2"},
        ],
    )
    score, reasons = score_validate_candidate(
        candidate,
        recent_scope_mix={
            "ai-automation": 10,
            "business-growth-ops": 11,
            "ecommerce-sellers": 9,
        },
        recent_lane_mix={
            "signal": 22,
            "hot": 5,
            "breakdown": 3,
        },
    )
    assert score < 0
    assert "signal_over_target" in reasons
