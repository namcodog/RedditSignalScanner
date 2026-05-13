from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.services.hotpost.card_payload_store import load_cards_payload


def _sample_draft(payload: dict) -> dict:
    card = dict(next(item for item in payload["published"] if item["card_type"] == "validate"))
    return {
        "draft_id": "draft-ai-large-repo",
        "candidate_id": "cand-ai-large-repo",
        "candidate_ids": ["cand-ai-large-repo"],
        "card_id": "draft-card-ai-large-repo",
        "signal_id": card["signal_id"],
        "card_type": card["card_type"],
        "category_id": card["category_id"],
        "title": card["title"],
        "source_scope_id": card["source_scope_id"],
        "source_scope_name": card["source_scope_name"],
        "matched_subreddit": "codex",
        "post_id": "abc123",
        "source_event_at": "2026-04-02T10:00:00Z",
        "score": 188,
        "num_comments": 42,
        "time_window": "7d",
        "signal_level": "rising",
        "why_now_reason": card["why_now_reason"],
        "thread_count": card["source_module"]["thread_count"],
        "community_count": card["source_module"]["community_count"],
        "quote_count": len(card["quotes"]),
        "intent_tags": card["intent_tags"],
        "evidence_quotes": card["quotes"],
        "summary_line": card["summary_line"],
        "audience": card["audience"],
        "why_now": card["why_now"],
        "source_link": card["source_link"],
        "source_links": [card["source_link"]],
        "source_communities": card["source_module"]["primary_communities"],
        "draft_status": "draft",
        "draft_note": "editor draft",
        "detail": card["detail"],
    }


@pytest.mark.asyncio
async def test_hotpost_card_drafts_start_empty(client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store

    path = tmp_path / "hotpost_cards.json"
    path.write_text(json.dumps({"categories": [], "candidates": [], "drafts": [], "published": []}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)

    resp = await client.get("/api/hotpost/card-drafts")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_hotpost_card_drafts_import_and_publish(client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store

    seed_payload = load_cards_payload()
    path = tmp_path / "hotpost_cards.json"
    path.write_text(json.dumps({"categories": [], "candidates": [], "drafts": [], "published": []}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)

    create_resp = await client.post("/api/hotpost/card-drafts", json={"card": _sample_draft(seed_payload)})
    assert create_resp.status_code == 200
    assert create_resp.json()["items"][0]["draft_id"] == "draft-ai-large-repo"

    publish_resp = await client.post("/api/hotpost/card-drafts/draft-ai-large-repo/publish")
    assert publish_resp.status_code == 200
    assert publish_resp.json()["card_id"] == "draft-card-ai-large-repo"

    payload = card_payload_store.load_cards_payload()
    assert payload["drafts"] == []
    assert len(payload["published"]) == 1
    assert payload["published"][0]["signal_level"] == "rising"
    assert payload["published"][0]["source_event_at"] == "2026-04-02T10:00:00Z"


@pytest.mark.asyncio
async def test_hotpost_card_drafts_support_type_filter(client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store

    seed_payload = load_cards_payload()
    path = tmp_path / "hotpost_cards.json"
    path.write_text(json.dumps({"categories": [], "candidates": [], "drafts": [], "published": []}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)
    assert (await client.post("/api/hotpost/card-drafts", json={"card": _sample_draft(seed_payload)})).status_code == 200
    resp = await client.get("/api/hotpost/card-drafts?card_type=validate")
    assert resp.status_code == 200
    assert all(item["card_type"] == "validate" for item in resp.json()["items"])
