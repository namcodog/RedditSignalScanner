from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from app.services.hotpost.card_payload_store import load_cards_payload


def _sample_candidate() -> dict:
    payload = load_cards_payload()
    card = payload["published"][0]
    return {
        "candidate_id": "cand-ai-001",
        "signal_id": card["signal_id"],
        "source_scope_id": card["source_scope_id"],
        "source_scope_name": card["source_scope_name"],
        "query": "cursor context drift",
        "matched_subreddit": "r/codex",
        "post_id": "abc123",
        "title": card["title"],
        "score": 188,
        "num_comments": 42,
        "created_at": card["published_at"],
        "collected_at": card["published_at"],
        "collect_batch_id": "ai-automation-20260404093000",
        "topic_pack_id": "agent-builder",
        "time_window": "7d",
        "signal_level": "rising",
        "why_now_reason": card["why_now_reason"],
        "listing_source": "search:relevance:week",
        "primary_reason": "problem_keyword",
        "matched_keywords": ["context drift"],
        "top_communities": ["r/codex"],
        "thread_count": 3,
        "community_count": 2,
        "quote_count": 3,
        "intent_tags": card["intent_tags"],
        "evidence_quotes": card["quotes"][:2],
    }


@pytest.mark.asyncio
async def test_hotpost_card_candidates_start_empty(client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store

    path = tmp_path / "hotpost_cards.json"
    path.write_text(json.dumps({"categories": [], "candidates": [], "drafts": [], "published": []}), encoding="utf-8")
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)
    response = await client.get("/api/hotpost/card-candidates")
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.asyncio
async def test_hotpost_card_candidates_import_and_draft(client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store
    from app.api.v1.endpoints import hotpost_card_candidates as endpoint_mod

    path = tmp_path / "hotpost_cards.json"
    path.write_text(json.dumps(load_cards_payload(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)
    async def _fake_generate(draft):
        return draft
    monkeypatch.setattr(endpoint_mod, "generate_card_content", _fake_generate)
    candidate = _sample_candidate()
    imported = await client.post("/api/hotpost/card-candidates", json={"candidate": candidate})
    assert imported.status_code == 200
    response = await client.post(f"/api/hotpost/card-candidates/{candidate['candidate_id']}/seed-draft", json={"card_type": "validate"})
    assert response.status_code == 200
    assert response.json()["items"][0]["draft_id"] == f"draft-{candidate['candidate_id']}-validate"


@pytest.mark.asyncio
async def test_hotpost_card_candidates_seed_draft_blocks_low_quality_signal_input(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services.hotpost import card_payload_store

    path = tmp_path / "hotpost_cards.json"
    path.write_text(json.dumps(load_cards_payload(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)
    candidate = _sample_candidate()
    candidate["thread_count"] = 1
    candidate["community_count"] = 1
    candidate["quote_count"] = 1
    candidate["evidence_quotes"] = [
        {
            "text": "Hi, hit me up if you ever want to chat",
            "community": "r/ChatGPT",
            "permalink": "https://www.reddit.com/r/ChatGPT/comments/weak/q1",
        }
    ]
    imported = await client.post("/api/hotpost/card-candidates", json={"candidate": candidate})
    assert imported.status_code == 200
    response = await client.post(f"/api/hotpost/card-candidates/{candidate['candidate_id']}/seed-draft", json={"card_type": "validate"})
    assert response.status_code == 409
    assert "Signal input quality gate blocked draft" in response.json()["detail"]


@pytest.mark.asyncio
async def test_hotpost_card_candidates_support_scope_filter(client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store

    path = tmp_path / "hotpost_cards.json"
    path.write_text(json.dumps(load_cards_payload(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)
    response = await client.get("/api/hotpost/card-candidates?source_scope_id=ai-automation")
    assert response.status_code == 200
    assert all(item["source_scope_id"] == "ai-automation" for item in response.json()["items"])


@pytest.mark.asyncio
async def test_hotpost_card_candidates_return_newest_first(client: AsyncClient) -> None:
    response = await client.get("/api/hotpost/card-candidates")
    assert response.status_code == 200
    collected_at = [item["collected_at"] for item in response.json()["items"]]
    assert collected_at == sorted(collected_at, reverse=True)


def test_hotpost_card_candidates_upsert_replaces_existing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.services.hotpost.card_candidate_store import get_candidate, upsert_candidate

    path = tmp_path / "hotpost_cards.json"
    path.write_text(json.dumps(load_cards_payload(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)
    candidate = CandidatePack.model_validate(_sample_candidate())
    upsert_candidate(candidate)
    updated = candidate.model_copy(update={"primary_reason": "problem_keyword", "matched_keywords": ["context drift"]})
    upsert_candidate(updated)
    saved = get_candidate(candidate.candidate_id)
    assert saved.primary_reason == "problem_keyword"
    assert saved.matched_keywords == ["context drift"]


def test_hotpost_card_candidates_replace_scope_candidates_drops_legacy_scope(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.services.hotpost.card_candidate_store import list_candidates, replace_scope_candidates

    path = tmp_path / "hotpost_cards.json"
    path.write_text(json.dumps(load_cards_payload(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)
    candidate = CandidatePack.model_validate(_sample_candidate())
    replace_scope_candidates("ai-automation", [candidate])
    items = list_candidates(source_scope_id="ai-automation")
    assert len(items) == 1
    assert items[0].candidate_id == candidate.candidate_id


@pytest.mark.asyncio
async def test_collect_scope_candidates_dedupes_same_post(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.schemas.hotpost_source_scopes import RedditSearchSpec
    from app.services.hotpost import candidate_spec_collector
    from app.services.hotpost import source_scope_candidate_collector as collector

    specs = [
        RedditSearchSpec(source_scope_id="ai-automation", topic_pack_id="agent-builder", subreddit="artificial", mode="listing", sort="hot", time_filter="day", listing_source="listing:hot:day", primary_reason="agent-builder:listing_hot"),
        RedditSearchSpec(source_scope_id="ai-automation", topic_pack_id="agent-builder", subreddit="artificial", mode="search", sort="relevance", time_filter="week", query="agent", listing_source="search:relevance:week", primary_reason="agent-builder:category_keyword", matched_keywords=["agent"]),
    ]
    post = SimpleNamespace(id="dup123", subreddit="artificial", title="Agent workflow pain", selftext="need better agent workflow", score=180, num_comments=42, created_utc=int(datetime.now(timezone.utc).timestamp()), permalink="/r/artificial/comments/dup123/test")

    class _FakeReddit:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False
        async def fetch_post_comments(self, *args, **kwargs): return [{"body": "This workflow keeps breaking once we add more than one agent.", "permalink": "/r/artificial/comments/dup123/test/c1"}]

    async def _fake_fetch_posts(reddit, spec, **_kwargs):
        return [post]

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: specs)
    monkeypatch.setattr(candidate_spec_collector, "fetch_posts_for_spec", _fake_fetch_posts)
    monkeypatch.setattr(collector, "build_collect_reddit_client", lambda *args, **kwargs: _FakeReddit())
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)
    items = await collector.collect_scope_candidates("ai-automation", max_candidates=8)
    assert len(items) == 1
    assert items[0].matched_keywords == ["agent"]
    assert items[0].topic_pack_id == "agent-builder"
