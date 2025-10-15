from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.services.community_pool_loader import CommunityPoolLoader


def _write_seed(tmp_path: Path) -> Path:
    data: dict[str, Any] = {
        "seed_communities": [
            {
                "name": "r/startups",
                "tier": "gold",
                "categories": ["startup", "business"],
                "description_keywords": ["startup", "founder"],
                "daily_posts": 150,
                "avg_comment_length": 80,
                "quality_score": 0.9,
            },
            {
                "name": "r/saas",
                "tier": "silver",
                "categories": ["saas"],
                "description_keywords": ["pricing", "mrr"],
                "daily_posts": 60,
                "avg_comment_length": 70,
                "quality_score": 0.75,
            },
        ]
    }
    p = tmp_path / "seed_communities.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.mark.asyncio
async def test_load_seed_communities(tmp_path: Path) -> None:
    seed_path = _write_seed(tmp_path)
    loader = CommunityPoolLoader(seed_path=seed_path)
    items = await loader.load_seed_communities()
    assert len(items) == 2
    assert items[0]["name"] == "r/startups"


@pytest.mark.asyncio
async def test_cache_refresh_logic(tmp_path: Path) -> None:
    seed_path = _write_seed(tmp_path)
    loader = CommunityPoolLoader(seed_path=seed_path)
    # No DB access in this test; ensure cache returns list and refresh toggles.
    # Monkeypatch the internal cache to simulate loaded content.
    loader._cache = []  # type: ignore[attr-defined]
    loader._last_refresh = None  # type: ignore[attr-defined]
    # Without DB, calling load_community_pool would attempt a session; skip by directly verifying should_refresh.
    assert loader._should_refresh() is True  # type: ignore[attr-defined]

