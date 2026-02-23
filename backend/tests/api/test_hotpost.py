from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.schemas.hotpost import HotpostSearchResponse
from app.services.hotpost.service import HotpostService


@pytest.mark.asyncio
async def test_hotpost_search_basic(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_search(self, request, user_id=None, session_id=None, ip_hash=None):
        return HotpostSearchResponse(
            query_id="test-id",
            query=request.query,
            mode="trending",
            search_time=datetime.now(timezone.utc),
            from_cache=False,
            summary="test summary",
            top_posts=[],
            key_comments=[],
            pain_points=None,
            opportunities=None,
            trending_keywords=None,
            communities=[],
            related_queries=[],
            evidence_count=0,
            community_distribution={},
            sentiment_overview={"positive": 0.0, "neutral": 0.0, "negative": 0.0},
            confidence="none",
        )

    async def _fake_close(self) -> None:
        return None

    monkeypatch.setattr(HotpostService, "search", _fake_search)
    monkeypatch.setattr(HotpostService, "close", _fake_close)

    resp = await client.post("/api/hotpost/search", json={"query": "robot vacuum"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "robot vacuum"
    assert data["mode"] == "trending"
