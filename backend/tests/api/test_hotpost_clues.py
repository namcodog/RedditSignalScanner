from __future__ import annotations

from collections import defaultdict

import pytest
from httpx import AsyncClient


class _FakeRedis:
    def __init__(self) -> None:
        self._hashes: dict[str, dict[str, int]] = defaultdict(dict)

    async def close(self) -> None:
        return None

    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        current = self._hashes[key].get(field, 0) + amount
        self._hashes[key][field] = current
        return current


@pytest.mark.asyncio
async def test_hotpost_categories_returns_product_categories(client: AsyncClient) -> None:
    resp = await client.get("/api/hotpost/categories")
    assert resp.status_code == 200
    assert [item["category_id"] for item in resp.json()["items"]] == ["all", "validate", "write"]


@pytest.mark.asyncio
async def test_hotpost_cards_support_type_filter_and_source_domain_fields(client: AsyncClient) -> None:
    resp = await client.get("/api/hotpost/cards", params={"card_type": "validate"})
    assert resp.status_code == 200
    assert all(item["card_type"] == "validate" for item in resp.json()["items"])
    assert all(item["lane"] == "signal" for item in resp.json()["items"])
    assert all(item["category_id"] == "validate" for item in resp.json()["items"])
    assert all(item["source_scope_id"] for item in resp.json()["items"])
    assert all(item["source_scope_name"] for item in resp.json()["items"])
    assert all(item["source_domain_id"] for item in resp.json()["items"])
    assert all(item["source_domain_name"] for item in resp.json()["items"])
    assert all("signal_level" in item for item in resp.json()["items"])
    assert all("source_event_at" in item for item in resp.json()["items"])
    assert all("thread_count" in item for item in resp.json()["items"])
    assert all("community_count" in item for item in resp.json()["items"])
    assert all("top_community" in item for item in resp.json()["items"])


@pytest.mark.asyncio
async def test_hotpost_cards_default_page_size_follows_supply_contract(client: AsyncClient) -> None:
    resp = await client.get("/api/hotpost/cards", params={"card_type": "all"})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 30


@pytest.mark.asyncio
async def test_hotpost_cards_reject_page_size_above_supply_contract(client: AsyncClient) -> None:
    resp = await client.get("/api/hotpost/cards", params={"card_type": "all", "page_size": 31})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_hotpost_cards_support_hot_lane_filter(client: AsyncClient) -> None:
    resp = await client.get("/api/hotpost/cards", params={"card_type": "hot"})
    assert resp.status_code == 200
    assert all(item["card_type"] == "validate" for item in resp.json()["items"])
    assert all(item["lane"] == "hot" for item in resp.json()["items"])


@pytest.mark.asyncio
async def test_hotpost_cards_support_supplement_surface(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import clues_catalog

    monkeypatch.setattr(
        clues_catalog,
        "_load_snapshot_cards",
        lambda: [
            {
                "card_id": "card-main-001",
                "signal_id": "sig-main-001",
                "card_type": "validate",
                "lane": "hot",
                "category_id": "validate",
                "source_scope_id": "ai-automation",
                "source_scope_name": "AI 与自动化",
                "source_domain_id": "reddit",
                "source_domain_name": "Reddit",
                "source_event_at": "2026-04-18T09:00:00Z",
                "title": "主前台卡",
                "summary_line": "主前台摘要",
                "audience": "工程师",
                "why_now": "why",
                "why_now_reason": "new_threads_24h",
                "signal_level": "hot",
                "intent_tags": ["热点"],
                "top_community": "r/ClaudeCode",
                "thread_count": 1,
                "community_count": 1,
                "preview_quote": {
                    "text": "quote",
                    "community": "r/ClaudeCode",
                    "permalink": "https://reddit.com/main",
                },
                "published_at": "2026-04-19T09:00:00Z",
                "source_module": {
                    "primary_communities": ["r/ClaudeCode"],
                    "top_community": "r/ClaudeCode",
                    "tone_tags": [],
                    "thread_count": 1,
                    "community_count": 1,
                    "last_active_text": "近24小时",
                },
                "surface_bucket": "main",
            },
            {
                "card_id": "card-supplement-001",
                "signal_id": "sig-supplement-001",
                "card_type": "validate",
                "lane": "signal",
                "category_id": "validate",
                "source_scope_id": "ai-automation",
                "source_scope_name": "AI 与自动化",
                "source_domain_id": "reddit",
                "source_domain_name": "Reddit",
                "source_event_at": "2026-04-10T09:00:00Z",
                "title": "15天补充卡",
                "summary_line": "补充摘要",
                "audience": "工程师",
                "why_now": "why",
                "why_now_reason": "recurring_7d",
                "signal_level": "rising",
                "intent_tags": ["补充"],
                "top_community": "r/LocalLLaMA",
                "thread_count": 1,
                "community_count": 1,
                "preview_quote": {
                    "text": "quote",
                    "community": "r/LocalLLaMA",
                    "permalink": "https://reddit.com/supplement",
                },
                "published_at": "2026-04-19T09:10:00Z",
                "source_module": {
                    "primary_communities": ["r/LocalLLaMA"],
                    "top_community": "r/LocalLLaMA",
                    "tone_tags": [],
                    "thread_count": 1,
                    "community_count": 1,
                    "last_active_text": "近15天",
                },
                "surface_bucket": "supplement",
            },
        ],
    )

    main_resp = await client.get("/api/hotpost/cards", params={"card_type": "all"})
    validate_resp = await client.get("/api/hotpost/cards", params={"card_type": "validate"})
    supplement_resp = await client.get("/api/hotpost/cards", params={"card_type": "supplement"})

    assert main_resp.status_code == 200
    assert [item["card_id"] for item in main_resp.json()["items"]] == ["card-main-001", "card-supplement-001"]
    assert validate_resp.status_code == 200
    assert [item["card_id"] for item in validate_resp.json()["items"]] == ["card-supplement-001"]
    assert supplement_resp.status_code == 200
    assert [item["card_id"] for item in supplement_resp.json()["items"]] == ["card-supplement-001"]


@pytest.mark.asyncio
async def test_hotpost_cards_follow_latest_mini_snapshot_order(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import clues_catalog

    monkeypatch.setattr(
        clues_catalog,
        "_load_snapshot_cards",
        lambda: [
            {
                "card_id": "card-hot-001",
                "signal_id": "sig-hot-001",
                "card_type": "validate",
                "lane": "hot",
                "category_id": "validate",
                "source_scope_id": "business-growth-ops",
                "source_scope_name": "商业增长与运营",
                "source_domain_id": "reddit",
                "source_domain_name": "Reddit",
                "source_event_at": "2026-04-14T09:00:00Z",
                "title": "首页第一张 hot",
                "summary_line": "hot 摘要",
                "audience": "运营",
                "why_now": "why",
                "why_now_reason": "new_threads_24h",
                "signal_level": "hot",
                "intent_tags": ["热点"],
                "top_community": "r/PPC",
                "thread_count": 1,
                "community_count": 1,
                "preview_quote": {
                    "text": "quote",
                    "community": "r/PPC",
                    "permalink": "https://reddit.com/1",
                },
                "published_at": "2026-04-14T09:00:00Z",
                "source_module": {
                    "primary_communities": ["r/PPC"],
                    "top_community": "r/PPC",
                    "tone_tags": [],
                    "thread_count": 1,
                    "community_count": 1,
                    "last_active_text": "1小时前",
                },
            },
            {
                "card_id": "card-breakdown-001",
                "signal_id": "sig-breakdown-001",
                "card_type": "write",
                "lane": "breakdown",
                "category_id": "write",
                "source_scope_id": "ecommerce-sellers",
                "source_scope_name": "电商与卖家",
                "source_domain_id": "reddit",
                "source_domain_name": "Reddit",
                "source_event_at": "2026-04-14T08:00:00Z",
                "title": "首页第二张 breakdown",
                "summary_line": "breakdown 摘要",
                "audience": "卖家",
                "why_now": "why",
                "why_now_reason": "recurring_7d",
                "intent_tags": ["争议"],
                "top_community": "r/BuyItForLife",
                "thread_count": 2,
                "community_count": 1,
                "preview_quote": {
                    "text": "quote",
                    "community": "r/BuyItForLife",
                    "permalink": "https://reddit.com/2",
                },
                "published_at": "2026-04-14T10:00:00Z",
                "source_module": {
                    "primary_communities": ["r/BuyItForLife"],
                    "top_community": "r/BuyItForLife",
                    "tone_tags": [],
                    "thread_count": 2,
                    "community_count": 1,
                    "last_active_text": "2小时前",
                },
            },
        ],
    )

    resp = await client.get("/api/hotpost/cards", params={"card_type": "all"})

    assert resp.status_code == 200
    assert [item["card_id"] for item in resp.json()["items"][:2]] == ["card-hot-001", "card-breakdown-001"]


@pytest.mark.asyncio
async def test_hotpost_cards_support_cursor_pagination(client: AsyncClient) -> None:
    first_page = await client.get("/api/hotpost/cards", params={"card_type": "all", "page_size": 2})
    assert first_page.status_code == 200
    assert len(first_page.json()["items"]) == 2
    assert first_page.json()["next_cursor"] is not None

    second_page = await client.get("/api/hotpost/cards", params={"card_type": "all", "page_size": 2, "cursor": first_page.json()["next_cursor"]})
    assert second_page.status_code == 200
    assert len(second_page.json()["items"]) == 2
    assert first_page.json()["items"][0]["card_id"] != second_page.json()["items"][0]["card_id"]


@pytest.mark.asyncio
async def test_hotpost_card_detail_returns_typed_detail(client: AsyncClient) -> None:
    listing = await client.get("/api/hotpost/cards", params={"card_type": "write"})
    card_id = listing.json()["items"][0]["card_id"]
    resp = await client.get(f"/api/hotpost/cards/{card_id}")
    assert resp.status_code == 200
    assert resp.json()["card_type"] == "write"
    assert "title_hooks" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_hotpost_hot_card_detail_accepts_controversy_meta(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import clues_catalog

    monkeypatch.setattr(
        clues_catalog,
        "load_published_cards",
        lambda: [
            {
                "card_id": "card-hot-current-001",
                "signal_id": "sig-hot-current-001",
                "card_type": "validate",
                "lane": "hot",
                "category_id": "validate",
                "source_scope_id": "ai-automation",
                "source_scope_name": "AI 与自动化",
                "source_domain_id": "reddit",
                "source_domain_name": "Reddit",
                "source_event_at": "2026-04-14T07:25:00Z",
                "title": "当前 hot 卡",
                "summary_line": "当前摘要",
                "audience": "运营",
                "why_now": "why now",
                "why_now_reason": "new_threads_24h",
                "signal_level": "hot",
                "intent_tags": ["舆情争议"],
                "top_community": "r/OpenAI",
                "thread_count": 4,
                "community_count": 2,
                "preview_quote": {
                    "text": "quote",
                    "community": "r/OpenAI",
                    "permalink": "https://www.reddit.com/r/OpenAI/comments/current/q1",
                },
                "published_at": "2026-04-14T08:00:00Z",
                "source_module": {
                    "primary_communities": ["r/OpenAI"],
                    "top_community": "r/OpenAI",
                    "tone_tags": [],
                    "thread_count": 4,
                    "community_count": 2,
                    "last_active_text": "1小时前",
                },
                "quotes": [
                    {
                        "text": "quote",
                        "community": "r/OpenAI",
                        "permalink": "https://www.reddit.com/r/OpenAI/comments/current/q1",
                    }
                ],
                "source_link": "https://www.reddit.com/r/OpenAI/comments/current",
                "detail": {
                    "flashpoint": "这帖突然炸起来。",
                    "fight_line": "评论区开始围绕动机站队。",
                    "why_test_now": "关键证据是评论已经开始分叉解释。",
                    "continue_signal": "继续看后续是否出现更多现实动作。",
                    "stop_signal": "如果只剩重复转述，就先放过。",
                },
                "controversy_chart": {
                    "support_ratio": 0.21,
                    "oppose_ratio": 0.5,
                    "neutral_ratio": 0.29,
                    "support_point": "先看能不能少手动维护。",
                    "oppose_point": "这只是富豪的安保问题，不是反人工智能情绪失控。",
                    "neutral_point": "还得看这次事件会不会影响人工智能的正常发展。",
                    "debate_focus": "这到底只是治安事件还是反人工智能情绪越线了？",
                    "dominant_side": "oppose",
                    "confidence": "high",
                },
                "controversy_meta": {
                    "post_id": "1sk82sc",
                    "sample_size": 36,
                    "sampled_at": "2026-04-14T07:25:00.957386Z",
                    "fetch_status": "ok",
                    "llm_summary_version": "cn_human_point_slots_v8",
                    "sample_quality": "high",
                    "summary_status": "ok",
                    "confidence_reason": "判断相对保守。",
                },
            }
        ],
    )

    resp = await client.get("/api/hotpost/cards/card-hot-current-001")

    assert resp.status_code == 200
    assert resp.json()["lane"] == "hot"
    assert resp.json()["controversy_meta"]["sample_size"] == 36
    assert resp.json()["controversy_chart"]["dominant_side"] == "oppose"


@pytest.mark.asyncio
async def test_hotpost_card_event_records_metric(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.v1.endpoints import hotpost_clues

    redis = _FakeRedis()
    monkeypatch.setattr(hotpost_clues.Redis, "from_url", lambda *args, **kwargs: redis)
    listing = await client.get("/api/hotpost/cards")
    card_id = listing.json()["items"][0]["card_id"]
    resp = await client.post("/api/hotpost/card-events", json={"type": "detail_view", "card_id": card_id, "category_id": "all"})

    assert resp.status_code == 200
    assert any("detail_view" in fields for fields in redis._hashes.values())


@pytest.mark.asyncio
async def test_hotpost_card_event_accepts_share_click(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.v1.endpoints import hotpost_clues

    redis = _FakeRedis()
    monkeypatch.setattr(hotpost_clues.Redis, "from_url", lambda *args, **kwargs: redis)
    listing = await client.get("/api/hotpost/cards")
    card_id = listing.json()["items"][0]["card_id"]

    resp = await client.post(
        "/api/hotpost/card-events",
        json={"type": "share_click", "card_id": card_id, "category_id": "all"},
    )

    assert resp.status_code == 200
    assert any("share_click" in fields for fields in redis._hashes.values())
