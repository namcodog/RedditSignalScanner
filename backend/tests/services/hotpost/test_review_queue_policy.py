from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.card_draft_builder import seed_validation_draft
from app.services.hotpost import card_review_rejection_store as rejection_store
from app.services.hotpost.review_queue_policy import filter_actionable_candidates


def _candidate(
    candidate_id: str,
    *,
    title: str,
    quotes: list[str],
    thread_count: int = 1,
    community_count: int = 1,
    score: int = 10,
    num_comments: int = 12,
) -> CandidatePack:
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return CandidatePack.model_validate(
        {
            "candidate_id": candidate_id,
            "signal_id": f"sig-{candidate_id}",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "topic_pack_id": "agent-builder",
            "query": "q",
            "matched_subreddit": "OpenAI",
            "post_id": "post",
            "title": title,
            "score": score,
            "num_comments": num_comments,
            "created_at": now_iso,
            "collected_at": now_iso,
            "collect_batch_id": "batch",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "switch_signal_7d",
            "listing_source": "listing:rising:day",
            "primary_reason": "reason",
            "matched_keywords": [],
            "top_communities": ["r/OpenAI"],
            "thread_count": thread_count,
            "community_count": community_count,
            "quote_count": len(quotes),
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [
                {"text": text, "community": "r/OpenAI", "permalink": f"https://reddit.com/{idx}"}
                for idx, text in enumerate(quotes, start=1)
            ],
        }
    )


def test_filter_actionable_candidates_skips_blocked_and_rejected(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(rejection_store, "REVIEW_REJECTIONS_PATH", tmp_path / "review_rejections.json")
    rejection_store.save_review_rejection("cand-rejected", reason="correct_but_empty")
    blocked = _candidate("cand-blocked", title="Need advice", quotes=["ok"])
    rich_quotes = [
        "Users are cancelling after the second failed handoff because the agent keeps losing context.",
        "We had to rewrite the workflow and add guardrails before the team trusted it again.",
    ]
    rejected = _candidate("cand-rejected", title="Useful title", quotes=rich_quotes, thread_count=2, community_count=2)
    kept = _candidate("cand-kept", title="Useful title", quotes=rich_quotes, thread_count=2, community_count=2)
    items = filter_actionable_candidates(
        [blocked, rejected, kept],
        card_type="validate",
        published_items=[],
        draft_items=[],
    )
    assert [item.candidate_id for item in items] == ["cand-kept"]


def test_filter_actionable_candidates_keeps_hot_even_if_signal_gate_would_block(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(rejection_store, "REVIEW_REJECTIONS_PATH", tmp_path / "review_rejections.json")
    hot_candidate = _candidate(
        "cand-hot",
        title="SEMrush charged me $211 using deceptive dark patterns to prevent trial cancellation",
        quotes=[
            "Classic SEMrush. Predatory company and the cancellation flow is clearly designed to trap you.",
            "A chargeback is the only thing that worked for me because support kept looping me around.",
        ],
        score=120,
        num_comments=40,
    )
    hot_candidate = CandidatePack.model_validate(
        {
            **hot_candidate.model_dump(mode="json"),
            "topic_pack_id": "upstream-winds",
            "topic_cluster_id": "platform-policy-shifts",
            "topic_cluster_ids": ["platform-policy-shifts"],
            "matched_subreddit": "ClaudeCode",
            "listing_source": "search:relevance:week",
            "intent_tags": ["求推荐"],
            "top_communities": ["r/ClaudeCode"],
            "evidence_quotes": [
                {
                    "text": "I canceled mine this morning and moved the team back after the pricing change landed.",
                    "community": "r/ClaudeCode",
                    "permalink": "https://reddit.com/1",
                },
                {
                    "text": "We switched this week because the new bill made the workflow too expensive to keep.",
                    "community": "r/ClaudeCode",
                    "permalink": "https://reddit.com/2",
                },
            ],
        }
    )
    items = filter_actionable_candidates(
        [hot_candidate],
        card_type="validate",
        published_items=[],
        draft_items=[],
    )
    assert [item.candidate_id for item in items] == ["cand-hot"]


def test_filter_actionable_candidates_blocks_hot_joke_signal(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(rejection_store, "REVIEW_REJECTIONS_PATH", tmp_path / "review_rejections.json")
    hot_candidate = _candidate(
        "cand-hot-joke",
        title="Fisher-Price Is Pivoting to AI-Powered Autonomous Weapons Manufacturing",
        quotes=[
            "This is a joke article btw",
            "Next thing you tell me is LEGO is making grenades.",
        ],
        score=120,
        num_comments=40,
    )
    items = filter_actionable_candidates(
        [hot_candidate],
        card_type="validate",
        published_items=[],
        draft_items=[],
    )
    assert items == []


def test_filter_actionable_candidates_ignores_incomplete_draft_blocker(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(rejection_store, "REVIEW_REJECTIONS_PATH", tmp_path / "review_rejections.json")
    candidate = _candidate(
        "cand-incomplete-draft",
        title="Useful title",
        quotes=[
            "Users are cancelling after the second failed handoff because the agent keeps losing context.",
            "We had to rewrite the workflow and add guardrails before the team trusted it again.",
        ],
        thread_count=2,
        community_count=2,
    )
    draft = seed_validation_draft(candidate).model_dump(mode="json")

    items = filter_actionable_candidates(
        [candidate],
        card_type="validate",
        published_items=[],
        draft_items=[draft],
    )

    assert [item.candidate_id for item in items] == ["cand-incomplete-draft"]
