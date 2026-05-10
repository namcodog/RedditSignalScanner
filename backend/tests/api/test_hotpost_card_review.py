from __future__ import annotations
import json
from pathlib import Path
import pytest
from httpx import AsyncClient
@pytest.mark.asyncio
async def test_hotpost_seed_group_draft_merges_candidates(client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store
    from app.api.v1.endpoints import hotpost_card_review as endpoint_mod
    path = tmp_path / "hotpost_cards.json"
    path.write_text(json.dumps({"categories": [], "candidates": [], "drafts": [], "published": []}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)
    async def _fake_generate(draft):
        return draft
    monkeypatch.setattr(endpoint_mod, "generate_card_content", _fake_generate)
    candidates = [
        {
            "candidate_id": "cand-ai-001",
            "signal_id": "sig-ai-001",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "query": "agents",
            "matched_subreddit": "artificial",
            "post_id": "a1",
            "title": "Agent systems keep failing silently",
            "score": 120,
            "num_comments": 45,
            "created_at": "2026-04-04T00:00:00Z",
            "collected_at": "2026-04-04T00:10:00Z",
            "collect_batch_id": "batch-ai-1",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "recurring_7d",
            "listing_source": "listing_hot",
            "primary_reason": "search_hit",
            "matched_keywords": ["agent", "failure"],
            "top_communities": ["r/artificial"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 2,
            "intent_tags": ["避坑"],
            "evidence_quotes": [{"text": "Silent failures are worse than crashes in agent systems.", "community": "r/artificial", "permalink": "https://www.reddit.com/r/artificial/comments/a1/test"}],
        },
        {
            "candidate_id": "cand-ai-002",
            "signal_id": "sig-ai-002",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "query": "agents",
            "matched_subreddit": "OpenAI",
            "post_id": "b2",
            "title": "Teams want provable AI actions before rollout",
            "score": 88,
            "num_comments": 32,
            "created_at": "2026-04-04T00:05:00Z",
            "collected_at": "2026-04-04T00:12:00Z",
            "collect_batch_id": "batch-ai-1",
            "time_window": "24h",
            "signal_level": "hot",
            "why_now_reason": "new_threads_24h",
            "listing_source": "listing_rising",
            "primary_reason": "new_threads_24h",
            "matched_keywords": ["agent", "audit"],
            "top_communities": ["r/OpenAI"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 2,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [
                {"text": "Welcome to /r/OpenAI and please read the rules first.", "community": "r/OpenAI", "permalink": "https://www.reddit.com/r/OpenAI/comments/b2/rules"},
                {"text": "If an AI tool cannot prove what it changed, enterprises will not trust it.", "community": "r/OpenAI", "permalink": "https://www.reddit.com/r/OpenAI/comments/b2/test"},
            ],
        },
    ]
    for item in candidates:
        assert (await client.post("/api/hotpost/card-candidates", json={"candidate": item})).status_code == 200
    resp = await client.post("/api/hotpost/card-review/seed-draft", json={"candidate_ids": ["cand-ai-001", "cand-ai-002"], "card_type": "validate"})
    assert resp.status_code == 200
    draft = resp.json()["items"][0]
    assert draft["thread_count"] == 2
    assert draft["community_count"] == 2
    assert draft["candidate_ids"] == ["cand-ai-001", "cand-ai-002"]
    assert draft["source_event_at"] == "2026-04-04T00:05:00Z"
    assert len(draft["evidence_quotes"]) == 2
    assert all(not item["text"].startswith("Welcome to /r/") for item in draft["evidence_quotes"])
@pytest.mark.asyncio
async def test_hotpost_breakdown_suggestions_groups_related_candidates(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services.hotpost import card_payload_store
    path = tmp_path / "hotpost_cards.json"
    path.write_text(json.dumps({"categories": [], "candidates": [], "drafts": [], "published": []}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)
    candidates = [
        {
            "candidate_id": "cand-ai-101",
            "signal_id": "sig-ai-101",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "topic_pack_id": "agent-builder",
            "query": "agent audit",
            "matched_subreddit": "artificial",
            "post_id": "p1",
            "title": "Agent systems keep failing silently",
            "score": 120,
            "num_comments": 45,
            "created_at": "2026-04-04T00:00:00Z",
            "collected_at": "2026-04-04T00:10:00Z",
            "collect_batch_id": "batch-ai-1",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "recurring_7d",
            "listing_source": "listing_hot",
            "primary_reason": "agent-builder:category_keyword",
            "matched_keywords": ["agent audit", "reliability"],
            "top_communities": ["r/artificial"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 2,
            "intent_tags": ["避坑"],
            "evidence_quotes": [{"text": "Silent failures are worse than crashes in agent systems.", "community": "r/artificial", "permalink": "https://www.reddit.com/r/artificial/comments/p1/test"}],
        },
        {
            "candidate_id": "cand-ai-102",
            "signal_id": "sig-ai-102",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "topic_pack_id": "agent-builder",
            "query": "agent audit",
            "matched_subreddit": "OpenAI",
            "post_id": "p2",
            "title": "Teams want provable AI actions before rollout",
            "score": 88,
            "num_comments": 32,
            "created_at": "2026-04-04T00:05:00Z",
            "collected_at": "2026-04-04T00:12:00Z",
            "collect_batch_id": "batch-ai-1",
            "time_window": "24h",
            "signal_level": "hot",
            "why_now_reason": "new_threads_24h",
            "listing_source": "listing_rising",
            "primary_reason": "agent-builder:problem_keyword",
            "matched_keywords": ["agent audit", "trust"],
            "top_communities": ["r/OpenAI"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 2,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [
                {"text": "If an AI tool cannot prove what it changed, enterprises will not trust it.", "community": "r/OpenAI", "permalink": "https://www.reddit.com/r/OpenAI/comments/p2/test"},
            ],
        },
        {
            "candidate_id": "cand-ai-103",
            "signal_id": "sig-ai-103",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "topic_pack_id": "agent-builder",
            "query": "agent audit",
            "matched_subreddit": "OpenAI",
            "post_id": "p3",
            "title": "Agents still fail the trust test without clear audit logs",
            "score": 72,
            "num_comments": 21,
            "created_at": "2026-04-04T01:00:00Z",
            "collected_at": "2026-04-04T01:02:00Z",
            "collect_batch_id": "batch-ai-1",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "recurring_7d",
            "listing_source": "listing_top",
            "primary_reason": "agent-builder:problem_keyword",
            "matched_keywords": ["agent audit", "trust"],
            "top_communities": ["r/OpenAI"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 1,
            "intent_tags": ["避坑"],
            "evidence_quotes": [{"text": "Without an audit trail, teams still treat agents like an unsafe black box.", "community": "r/OpenAI", "permalink": "https://www.reddit.com/r/OpenAI/comments/p3/test"}],
        },
    ]
    for item in candidates:
        assert (await client.post("/api/hotpost/card-candidates", json={"candidate": item})).status_code == 200
    resp = await client.get("/api/hotpost/card-review/suggestions?source_scope_id=ai-automation")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    suggestion = items[0]
    assert suggestion["topic_pack_id"] == "agent-builder"
    assert suggestion["candidate_ids"] == ["cand-ai-101", "cand-ai-102", "cand-ai-103"]
    assert suggestion["thread_count"] == 3
    assert suggestion["community_count"] == 2
    assert "keyword_overlap" in suggestion["reason_codes"]
    assert suggestion["hypothesis"]
