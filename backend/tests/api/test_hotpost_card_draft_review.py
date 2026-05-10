from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.services.hotpost.card_payload_store import load_cards_payload


@pytest.mark.asyncio
async def test_hotpost_draft_update_and_publish(client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store
    from app.api.v1.endpoints import hotpost_card_candidates as endpoint_mod

    path = tmp_path / "hotpost_cards.json"
    path.write_text(json.dumps(load_cards_payload(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)
    async def _fake_generate(draft):
        return draft
    monkeypatch.setattr(endpoint_mod, "generate_card_content", _fake_generate)

    candidate = {
        "candidate_id": "cand-ai-review-001",
        "signal_id": "sig-ai-review-001",
        "source_scope_id": "ai-automation",
        "source_scope_name": "AI 与自动化",
        "query": "workflow",
        "matched_subreddit": "artificial",
        "post_id": "abc123",
        "title": "AI workflow pain is getting louder",
        "score": 188,
        "num_comments": 42,
        "created_at": "2026-04-04T00:00:00Z",
        "collected_at": "2026-04-04T00:10:00Z",
        "collect_batch_id": "batch-ai-review-001",
        "time_window": "7d",
        "signal_level": "rising",
        "why_now_reason": "recurring_7d",
        "listing_source": "search:relevance:week",
        "primary_reason": "problem_keyword",
        "matched_keywords": ["workflow"],
        "top_communities": ["r/artificial"],
        "thread_count": 1,
        "community_count": 1,
        "quote_count": 1,
        "intent_tags": ["趋势变化"],
        "evidence_quotes": [{"text": "Teams keep complaining about broken AI workflow context.", "community": "r/artificial", "permalink": "https://www.reddit.com/r/artificial/comments/abc123/test"}],
    }
    assert (await client.post("/api/hotpost/card-candidates", json={"candidate": candidate})).status_code == 200
    seeded = await client.post("/api/hotpost/card-candidates/cand-ai-review-001/seed-draft", json={"card_type": "validate"})
    assert seeded.status_code == 200
    draft = seeded.json()["items"][0]
    draft["summary_line"] = "不少团队已经把 AI workflow 的上下文丢失当成真实阻塞。"
    draft["audience"] = "多工具协作、流程较长的团队"
    draft["why_now"] = "近 7 天里，这类抱怨在多个讨论里反复出现。"
    draft["detail"] = {
        "pain_point": "AI 工具在长流程里经常丢上下文。",
        "target_user_and_scene": "协作流程长、任务切换多的团队。",
        "why_test_now": "用户已经把抱怨从吐槽升级成替换意向。",
        "min_test_action": "先做 5 个访谈，确认上下文丢失是否是主阻塞。",
        "continue_signal": "访谈里有多人愿意为更稳的流程控制付费。",
        "stop_signal": "用户只在单一工具上抱怨，不构成独立需求。",
    }
    updated = await client.put(f"/api/hotpost/card-drafts/{draft['draft_id']}", json={"card": draft})
    assert updated.status_code == 200
    published = await client.post(f"/api/hotpost/card-drafts/{draft['draft_id']}/publish")
    assert published.status_code == 200
