from __future__ import annotations

from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.breakdown_suggestion_quality import assess_breakdown_suggestion_coherence


def _candidate(candidate_id: str, *, keyword: str, query: str, title: str) -> CandidatePack:
    return CandidatePack.model_validate(
        {
            "candidate_id": candidate_id,
            "signal_id": f"sig-{candidate_id}",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "topic_pack_id": "agent-builder",
            "query": query,
            "matched_subreddit": "OpenAI",
            "post_id": candidate_id,
            "title": title,
            "score": 1,
            "num_comments": 1,
            "created_at": "2026-04-08T00:00:00Z",
            "collected_at": "2026-04-08T00:00:00Z",
            "collect_batch_id": "b",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "recurring_7d",
            "listing_source": "search",
            "primary_reason": "test",
            "matched_keywords": [keyword],
            "top_communities": ["r/OpenAI"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 1,
            "intent_tags": ["避坑"],
            "evidence_quotes": [{"text": title, "community": "r/OpenAI", "permalink": f"https://reddit.com/{candidate_id}"}],
        }
    )


def test_assess_breakdown_suggestion_coherence_blocks_unrelated_pairs() -> None:
    quality = assess_breakdown_suggestion_coherence(
        [
            _candidate("a", keyword="sql reliability", query="sql reliability", title="Cursor keeps generating odd SQL"),
            _candidate("b", keyword="vibe coded repos", query="repo scan", title="I scanned 10 popular vibe coded repos"),
        ]
    )
    assert quality["should_block"] is True
    assert "weak_anchor_overlap" in quality["reasons"]


def test_assess_breakdown_suggestion_coherence_keeps_shared_anchor_pairs() -> None:
    quality = assess_breakdown_suggestion_coherence(
        [
            _candidate("a", keyword="agent audit trail", query="agent audit trail", title="Agents need audit trail before rollout"),
            _candidate("b", keyword="agent audit trail", query="agent audit trail", title="Audit trail is the blocker for enterprise agents"),
        ]
    )
    assert quality["should_block"] is False
    assert "agent" not in quality["shared_anchors"]
    assert "audit" in quality["shared_anchors"] or "trail" in quality["shared_anchors"]


def test_assess_breakdown_suggestion_coherence_allows_shared_keyword_when_quote_is_thin() -> None:
    first = _candidate(
        "a",
        keyword="tool calling unreliable",
        query="tool calling unreliable",
        title="Cursor keeps generating odd SQL and it is making me nervous",
    )
    second = _candidate(
        "b",
        keyword="tool calling unreliable",
        query="tool calling unreliable",
        title="The native editor chat breaks complex file dependencies",
    )
    second.evidence_quotes = []
    quality = assess_breakdown_suggestion_coherence([first, second])
    assert quality["should_block"] is False
    assert "unreliable" in quality["shared_anchors"] or "calling" in quality["shared_anchors"]
