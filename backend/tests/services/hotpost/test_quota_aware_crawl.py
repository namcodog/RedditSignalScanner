from __future__ import annotations

from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.quota_aware_crawl import build_enrich_shortlist


def _candidate(
    candidate_id: str,
    *,
    cluster: str,
    score: int,
    num_comments: int,
) -> CandidatePack:
    return CandidatePack.model_validate(
        {
            "candidate_id": candidate_id,
            "signal_id": f"sig-{candidate_id}",
            "source_scope_id": "ecommerce-sellers",
            "source_scope_name": "电商与卖家",
            "topic_pack_id": "selection-signals",
            "topic_cluster_id": cluster,
            "topic_cluster_ids": [cluster],
            "query": "query",
            "matched_subreddit": "Frugal",
            "post_id": candidate_id,
            "title": candidate_id,
            "score": score,
            "num_comments": num_comments,
            "created_at": "2026-04-19T00:00:00Z",
            "collected_at": "2026-04-19T00:00:00Z",
            "collect_batch_id": "batch-1",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "new_threads_24h",
            "listing_source": "search:relevance:week",
            "primary_reason": "selection-signals:scenario_keyword",
            "matched_keywords": ["query"],
            "top_communities": ["r/Frugal"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 0,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [],
        }
    )


def test_build_enrich_shortlist_keeps_priority_cluster_candidates_even_when_scores_are_lower() -> None:
    shortlist = build_enrich_shortlist(
        [
            _candidate("cand-edc-1", cluster="edc", score=200, num_comments=120),
            _candidate("cand-outdoor-1", cluster="outdoor", score=180, num_comments=110),
            _candidate("cand-home-1", cluster="home", score=160, num_comments=100),
            _candidate("cand-small-1", cluster="small-goods", score=40, num_comments=20),
            _candidate("cand-small-2", cluster="small-goods", score=35, num_comments=18),
        ],
        max_items=3,
    )

    assert [candidate.candidate_id for candidate in shortlist[:3]] == [
        "cand-edc-1",
        "cand-outdoor-1",
        "cand-home-1",
    ]
    assert {candidate.candidate_id for candidate in shortlist} >= {
        "cand-small-1",
        "cand-small-2",
    }
