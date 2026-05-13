from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_hotpost_collect_scope_candidates(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.v1.endpoints import hotpost_candidate_collection

    async def _fake_collect(_scope_id: str, *, max_candidates: int = 8) -> list[dict]:
        return [
            {
                "candidate_id": "cand-ai-001",
                "signal_id": "sig-001",
                "source_scope_id": "ai-automation",
                "source_scope_name": "AI 与自动化",
                "query": "workflow",
                "matched_subreddit": "artificial",
                "post_id": "abc123",
                "title": "AI workflow tool fatigue is getting worse",
                "score": 188,
                "num_comments": 42,
                "created_at": "2026-04-04T00:00:00Z",
                "collected_at": "2026-04-04T01:00:00Z",
                "collect_batch_id": "ai-automation-20260404010000",
                "time_window": "7d",
                "signal_level": "rising",
                "why_now_reason": "recurring_7d",
                "listing_source": "search:relevance:week",
                "primary_reason": "workflow:template_query",
                "thread_count": 1,
                "community_count": 1,
                "quote_count": 1,
                "intent_tags": ["趋势变化"],
                "evidence_quotes": [],
            }
        ]

    monkeypatch.setattr(hotpost_candidate_collection, "collect_scope_candidates", _fake_collect)
    response = await client.post("/api/hotpost/source-scopes/ai-automation/collect-candidates")
    assert response.status_code == 200
    assert response.json()["items"][0]["candidate_id"] == "cand-ai-001"
