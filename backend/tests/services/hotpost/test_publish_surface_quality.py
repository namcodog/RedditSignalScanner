from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.publish_surface_quality import assess_publish_surface_candidate


def _candidate(
    candidate_id: str,
    *,
    pack: str,
    cluster: str,
    title: str,
    created_at: datetime | None = None,
) -> CandidatePack:
    now = created_at or datetime.now(timezone.utc)
    return CandidatePack.model_validate(
        {
            "candidate_id": candidate_id,
            "signal_id": f"sig-{candidate_id}",
            "source_scope_id": "ai-automation" if pack in {"upstream-winds", "tools-efficiency"} else "business-growth-ops",
            "source_scope_name": "scope",
            "topic_pack_id": pack,
            "topic_cluster_id": cluster,
            "topic_cluster_ids": [cluster],
            "named_topic_ids": [],
            "query": "pricing update",
            "matched_subreddit": "OpenAI",
            "post_id": f"post-{candidate_id}",
            "title": title,
            "score": 220,
            "num_comments": 44,
            "created_at": now,
            "collected_at": now,
            "collect_batch_id": "batch-1",
            "time_window": "24h",
            "signal_level": "rising",
            "why_now_reason": "new_threads_24h",
            "listing_source": "listing:hot:day",
            "primary_reason": f"{pack}:listing_hot",
            "matched_keywords": ["pricing update"],
            "top_communities": ["r/OpenAI"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 2,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [
                {
                    "text": "The workflow changed in a real way: people are dropping manual handoffs because the new release finally handles the ugly edge cases.",
                    "community": "r/OpenAI",
                    "permalink": "https://www.reddit.com/r/OpenAI/comments/post-1/q1",
                },
                {
                    "text": "This is not just another tool mention. Teams are rewriting the route map because the old workaround is now slower than the native flow.",
                    "community": "r/OpenAI",
                    "permalink": "https://www.reddit.com/r/OpenAI/comments/post-1/q2",
                },
            ],
        }
    )


def test_exploration_tier_allows_single_thread_for_thin_pack() -> None:
    candidate = _candidate(
        "cand-thin",
        pack="funnel-conversion",
        cluster="funnel",
        title="The checkout rewrite exposed a real conversion leak",
    )

    result = assess_publish_surface_candidate(candidate, lane="signal")

    assert result["tier"] == "exploration"
    assert result["should_block"] is False
    assert set(result["relaxed_reasons"]) == {
        "single_thread_weak_evidence",
        "single_community_weak_evidence",
    }


def test_strong_tier_keeps_same_single_thread_candidate_blocked() -> None:
    candidate = _candidate(
        "cand-strong",
        pack="paid-economics",
        cluster="ads",
        title="The channel mix cracked after the pricing update",
    )

    result = assess_publish_surface_candidate(candidate, lane="signal")

    assert result["tier"] == "strong"
    assert result["should_block"] is True
    assert "single_thread_weak_evidence" in result["reasons"]
    assert "single_community_weak_evidence" in result["reasons"]


def test_exploration_tier_allows_new_cluster_under_strong_pack() -> None:
    candidate = _candidate(
        "cand-small-goods",
        pack="selection-signals",
        cluster="small-goods",
        title="Small replacement parts are quietly becoming the repeat-buy wedge",
    )

    result = assess_publish_surface_candidate(candidate, lane="signal")

    assert result["tier"] == "exploration"
    assert result["should_block"] is False


def test_hard_reject_still_blocks_exploration_candidate() -> None:
    candidate = _candidate(
        "cand-joke",
        pack="upstream-winds",
        cluster="platform-policy-shifts",
        title="Fisher-Price Is Pivoting to AI-Powered Autonomous Weapons Manufacturing",
    )
    candidate = candidate.model_copy(
        update={
            "evidence_quotes": [
                {"text": "This is a joke article btw", "community": "r/OpenAI", "permalink": "https://example.com/1"},
                {"text": "Next thing you tell me is LEGO is making grenades.", "community": "r/OpenAI", "permalink": "https://example.com/2"},
            ]
        }
    )

    result = assess_publish_surface_candidate(candidate, lane="signal")

    assert result["tier"] == "exploration"
    assert result["should_block"] is True
    assert "joke_or_satire_low_signal" in result["reasons"]


def test_exploration_tier_gets_light_freshness_relax() -> None:
    stale_but_relevant = datetime.now(timezone.utc) - timedelta(hours=30)
    candidate = _candidate(
        "cand-freshness",
        pack="upstream-winds",
        cluster="platform-policy-shifts",
        title="The platform release forced teams to redraw the route map",
        created_at=stale_but_relevant,
    )

    exploration = assess_publish_surface_candidate(candidate, lane="hot")
    strong = assess_publish_surface_candidate(
        candidate.model_copy(update={"topic_pack_id": "paid-economics", "topic_cluster_id": "ads", "topic_cluster_ids": ["ads"]}),
        lane="hot",
    )

    assert exploration["tier"] == "exploration"
    assert exploration["should_block"] is False
    assert strong["tier"] == "strong"
    assert strong["should_block"] is True
    assert "strong_lane_stale" in strong["reasons"]
