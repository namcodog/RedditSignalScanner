from __future__ import annotations

import os
import pytest

os.environ.setdefault("SKIP_DB_RESET", "1")

from app.services.analysis.pain_cluster import cluster_pain_points_auto


class FakeSession:
    async def execute(self, *args, **kwargs):  # pragma: no cover - simple stub
        raise RuntimeError("db unavailable")


@pytest.mark.asyncio
async def test_cluster_pain_points_auto_fallback():
    items = [
        {"description": "fee too high", "frequency": 5, "sentiment_score": -0.4, "severity": "medium", "example_posts": []},
        {"description": "slow payout", "frequency": 3, "sentiment_score": -0.3, "severity": "medium", "example_posts": []},
    ]
    clusters = await cluster_pain_points_auto(
        FakeSession(),
        since_days=30,
        subreddits=["r/test"],
        fallback_items=items,
        min_clusters=1,
        max_clusters=2,
    )
    assert clusters
    assert clusters[0].get("topic")
