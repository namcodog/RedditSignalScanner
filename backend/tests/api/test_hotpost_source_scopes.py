from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_hotpost_source_scopes_list(client: AsyncClient) -> None:
    response = await client.get("/api/hotpost/source-scopes")
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["source_scope_id"] for item in items] == [
        "ai-automation",
        "ecommerce-sellers",
        "business-growth-ops",
    ]
    ecommerce = next(item for item in items if item["source_scope_id"] == "ecommerce-sellers")
    assert [pack["topic_pack_id"] for pack in ecommerce["topic_packs"]] == [
        "selection-signals",
        "category-winds",
        "kill-signals",
    ]


@pytest.mark.asyncio
async def test_hotpost_source_scope_search_specs(client: AsyncClient) -> None:
    response = await client.get("/api/hotpost/source-scopes/ai-automation/search-specs")
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(
        item["mode"] == "listing"
        and item["topic_pack_id"] == "upstream-winds"
        and item["subreddit"] == "artificial"
        and item["listing_source"] == "listing:hot:day"
        for item in items
    )
    assert any(
        item["mode"] == "search"
        and item["query"] == "ai workflow with fewer tools"
        and item["topic_pack_id"] == "tools-efficiency"
        and item["topic_cluster_id"] == "workflow-friction"
        and item["primary_reason"] == "tools-efficiency:category_keyword"
        and item["matched_keywords"] == ["ai workflow with fewer tools"]
        for item in items
    )
