from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_hotpost_seed_group_draft_from_suggestion(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
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
            "candidate_id": "cand-ecom-301",
            "signal_id": "sig-ecom-301",
            "source_scope_id": "ecommerce-sellers",
            "source_scope_name": "电商卖家",
            "topic_pack_id": "selection-signals",
            "query": "stainless drink dispenser",
            "matched_subreddit": "BuyItForLife",
            "post_id": "p301",
            "title": "Glass drink dispensers crack at the spout",
            "score": 92,
            "num_comments": 26,
            "created_at": "2026-04-07T00:00:00Z",
            "collected_at": "2026-04-07T00:10:00Z",
            "collect_batch_id": "batch-ecom-1",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "recurring_7d",
            "listing_source": "listing_top",
            "primary_reason": "selection-signals:problem_keyword",
            "matched_keywords": ["stainless drink dispenser"],
            "top_communities": ["r/BuyItForLife"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 1,
            "intent_tags": ["求推荐"],
            "evidence_quotes": [{"text": "The spout cracks first, so I stopped trusting glass ones.", "community": "r/BuyItForLife", "permalink": "https://www.reddit.com/r/BuyItForLife/comments/p301/test"}],
        },
        {
            "candidate_id": "cand-ecom-302",
            "signal_id": "sig-ecom-302",
            "source_scope_id": "ecommerce-sellers",
            "source_scope_name": "电商卖家",
            "topic_pack_id": "selection-signals",
            "query": "stainless drink dispenser",
            "matched_subreddit": "Coffee",
            "post_id": "p302",
            "title": "People are replacing decorative glass dispensers with metal ones",
            "score": 77,
            "num_comments": 19,
            "created_at": "2026-04-07T01:00:00Z",
            "collected_at": "2026-04-07T01:10:00Z",
            "collect_batch_id": "batch-ecom-1",
            "time_window": "24h",
            "signal_level": "hot",
            "why_now_reason": "new_threads_24h",
            "listing_source": "listing_hot",
            "primary_reason": "selection-signals:problem_keyword",
            "matched_keywords": ["stainless drink dispenser"],
            "top_communities": ["r/Coffee"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 1,
            "intent_tags": ["替换"],
            "evidence_quotes": [{"text": "Pretty glass loses its appeal if the weak point is obvious.", "community": "r/Coffee", "permalink": "https://www.reddit.com/r/Coffee/comments/p302/test"}],
        },
        {
            "candidate_id": "cand-ecom-303",
            "signal_id": "sig-ecom-303",
            "source_scope_id": "ecommerce-sellers",
            "source_scope_name": "电商卖家",
            "topic_pack_id": "selection-signals",
            "query": "stainless drink dispenser",
            "matched_subreddit": "BuyItForLife",
            "post_id": "p303",
            "title": "People only care about the pretty shape until the weak joint fails",
            "score": 61,
            "num_comments": 11,
            "created_at": "2026-04-07T02:00:00Z",
            "collected_at": "2026-04-07T02:10:00Z",
            "collect_batch_id": "batch-ecom-1",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "recurring_7d",
            "listing_source": "listing_top",
            "primary_reason": "selection-signals:problem_keyword",
            "matched_keywords": ["stainless drink dispenser"],
            "top_communities": ["r/BuyItForLife"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 1,
            "intent_tags": ["避坑"],
            "evidence_quotes": [{"text": "The buying question shifts fast once the weak joint shows up in real use.", "community": "r/BuyItForLife", "permalink": "https://www.reddit.com/r/BuyItForLife/comments/p303/test"}],
        },
    ]
    for item in candidates:
        assert (await client.post("/api/hotpost/card-candidates", json={"candidate": item})).status_code == 200

    suggestions = await client.get("/api/hotpost/card-review/suggestions?source_scope_id=ecommerce-sellers")
    assert suggestions.status_code == 200
    suggestion_id = suggestions.json()["items"][0]["suggestion_id"]

    resp = await client.post(
        "/api/hotpost/card-review/seed-draft-from-suggestion",
        json={"suggestion_id": suggestion_id, "card_type": "write"},
    )

    assert resp.status_code == 200
    draft = resp.json()["items"][0]
    assert draft["candidate_ids"] == ["cand-ecom-301", "cand-ecom-302", "cand-ecom-303"]
    assert draft["card_type"] == "write"
    assert draft["thread_count"] == 3
    assert draft["community_count"] == 2


@pytest.mark.asyncio
async def test_hotpost_materialize_breakdown_drafts_endpoint(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services.hotpost import card_payload_store
    from app.api.v1.endpoints import hotpost_card_review as endpoint_mod

    path = tmp_path / "hotpost_cards.json"
    path.write_text(json.dumps({"categories": [], "candidates": [], "drafts": [], "published": []}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)

    async def _fake_materialize(source_scope_id=None, *, limit=20):
        from app.schemas.hotpost_card_review import BreakdownDraftMaterializeResult

        return [
            BreakdownDraftMaterializeResult(
                suggestion_id="suggestion-ai-1",
                status="materialized",
                draft_id="draft-group-ai-1",
                card_id="card-group-ai-1",
            )
        ]

    monkeypatch.setattr(endpoint_mod, "materialize_breakdown_drafts", _fake_materialize)
    resp = await client.post("/api/hotpost/card-review/materialize-drafts?source_scope_id=ai-automation&limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"][0]["status"] == "materialized"
    assert body["items"][0]["draft_id"] == "draft-group-ai-1"
