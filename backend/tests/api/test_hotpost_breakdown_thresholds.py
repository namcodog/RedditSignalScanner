from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_hotpost_breakdown_suggestions_hide_weak_pairs(
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
            "candidate_id": "cand-ai-401",
            "signal_id": "sig-ai-401",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "topic_pack_id": "agent-builder",
            "query": "agent audit",
            "matched_subreddit": "OpenAI",
            "post_id": "p401",
            "title": "Agents need proof of actions",
            "score": 70,
            "num_comments": 15,
            "created_at": "2026-04-07T00:00:00Z",
            "collected_at": "2026-04-07T00:10:00Z",
            "collect_batch_id": "batch-ai-2",
            "time_window": "24h",
            "signal_level": "hot",
            "why_now_reason": "new_threads_24h",
            "listing_source": "listing_top",
            "primary_reason": "agent-builder:test",
            "matched_keywords": ["agent audit"],
            "top_communities": ["r/OpenAI"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 1,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [{"text": "Enterprises want proof of actions before rollout.", "community": "r/OpenAI", "permalink": "https://www.reddit.com/r/OpenAI/comments/p401/test"}],
        },
        {
            "candidate_id": "cand-ai-402",
            "signal_id": "sig-ai-402",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "topic_pack_id": "agent-builder",
            "query": "agent audit",
            "matched_subreddit": "artificial",
            "post_id": "p402",
            "title": "Teams still do not trust silent agents",
            "score": 64,
            "num_comments": 18,
            "created_at": "2026-04-07T00:30:00Z",
            "collected_at": "2026-04-07T00:40:00Z",
            "collect_batch_id": "batch-ai-2",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "recurring_7d",
            "listing_source": "listing_hot",
            "primary_reason": "agent-builder:test",
            "matched_keywords": ["agent audit"],
            "top_communities": ["r/artificial"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 1,
            "intent_tags": ["避坑"],
            "evidence_quotes": [{"text": "Silent agent failures kill trust fast.", "community": "r/artificial", "permalink": "https://www.reddit.com/r/artificial/comments/p402/test"}],
        },
    ]
    for item in candidates:
        assert (await client.post("/api/hotpost/card-candidates", json={"candidate": item})).status_code == 200

    suggestions = await client.get("/api/hotpost/card-review/suggestions?source_scope_id=ai-automation")
    assert suggestions.status_code == 200
    assert suggestions.json()["items"] == []
