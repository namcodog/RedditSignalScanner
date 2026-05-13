from __future__ import annotations

from pathlib import Path

import pytest


def _seeded_path(tmp_path: Path) -> Path:
    path = tmp_path / "hotpost_cards.json"
    path.write_text('{"categories":[],"candidates":[],"drafts":[],"published":[]}', encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_materialize_breakdown_drafts_creates_write_draft(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store
    from app.services.hotpost import breakdown_draft_materializer as mod
    from app.services.hotpost.card_candidate_store import save_candidate
    from app.services.hotpost.card_group_draft_builder import seed_group_writing_draft
    from app.schemas.hotpost_card_candidates import CandidatePack

    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", _seeded_path(tmp_path))

    candidates = [
        CandidatePack.model_validate(
            {
                "candidate_id": "cand-a",
                "signal_id": "sig-a",
                "source_scope_id": "ai-automation",
                "source_scope_name": "AI 与自动化",
                "topic_pack_id": "agent-builder",
                "query": "agent audit trail",
                "matched_subreddit": "OpenAI",
                "post_id": "p1",
                "title": "Agents need audit trail before rollout",
                "score": 20,
                "num_comments": 8,
                "created_at": "2026-04-08T00:00:00Z",
                "collected_at": "2026-04-08T00:00:00Z",
                "collect_batch_id": "batch-1",
                "time_window": "7d",
                "signal_level": "rising",
                "why_now_reason": "recurring_7d",
                "listing_source": "search",
                "primary_reason": "agent-builder:test",
                "matched_keywords": ["agent audit trail"],
                "top_communities": ["r/OpenAI"],
                "thread_count": 1,
                "community_count": 1,
                "quote_count": 1,
                "intent_tags": ["避坑"],
                "evidence_quotes": [{"text": "Agents need an audit trail before enterprises trust them in production.", "community": "r/OpenAI", "permalink": "https://reddit.com/p1"}],
            }
        ),
        CandidatePack.model_validate(
            {
                "candidate_id": "cand-b",
                "signal_id": "sig-b",
                "source_scope_id": "ai-automation",
                "source_scope_name": "AI 与自动化",
                "topic_pack_id": "agent-builder",
                "query": "agent audit trail",
                "matched_subreddit": "cursor",
                "post_id": "p2",
                "title": "Audit trail is the blocker for enterprise agents",
                "score": 18,
                "num_comments": 7,
                "created_at": "2026-04-08T01:00:00Z",
                "collected_at": "2026-04-08T01:00:00Z",
                "collect_batch_id": "batch-1",
                "time_window": "7d",
                "signal_level": "rising",
                "why_now_reason": "recurring_7d",
                "listing_source": "search",
                "primary_reason": "agent-builder:test",
                "matched_keywords": ["agent audit trail"],
                "top_communities": ["r/cursor"],
                "thread_count": 1,
                "community_count": 1,
                "quote_count": 1,
                "intent_tags": ["趋势变化"],
                "evidence_quotes": [
                    {"text": "Without an audit trail, teams cannot inspect what agents actually did.", "community": "r/cursor", "permalink": "https://reddit.com/p2"},
                    {"text": "Teams only trust enterprise agents once the audit trail is inspectable.", "community": "r/cursor", "permalink": "https://reddit.com/p2b"},
                ],
            }
        ),
    ]
    for item in candidates:
        save_candidate(item)

    async def _fake_generate(draft):
        seeded = seed_group_writing_draft(candidates)
        return seeded.model_copy(update={"title": "Agent tool calling 还没到可托管阶段"})

    monkeypatch.setattr(mod, "generate_card_content", _fake_generate)
    results = await mod.materialize_breakdown_drafts(limit=10)
    assert len(results) == 1
    assert results[0].status == "materialized"


@pytest.mark.asyncio
async def test_materialize_breakdown_drafts_reports_failed_when_write_bar_drops(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store
    from app.services.hotpost import breakdown_draft_materializer as mod
    from app.services.hotpost.card_candidate_store import save_candidate
    from app.services.hotpost.card_group_draft_builder import seed_group_validation_draft
    from app.schemas.hotpost_card_candidates import CandidatePack

    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", _seeded_path(tmp_path))

    base = {
        "signal_id": "sig-a",
        "source_scope_id": "ai-automation",
        "source_scope_name": "AI 与自动化",
        "topic_pack_id": "agent-builder",
        "query": "agent audit trail",
        "score": 20,
        "num_comments": 8,
        "created_at": "2026-04-08T00:00:00Z",
        "collected_at": "2026-04-08T00:00:00Z",
        "collect_batch_id": "batch-1",
        "time_window": "7d",
        "signal_level": "rising",
        "why_now_reason": "recurring_7d",
        "listing_source": "search",
        "primary_reason": "agent-builder:test",
        "matched_keywords": ["agent audit trail"],
        "thread_count": 1,
        "community_count": 1,
        "quote_count": 1,
    }
    save_candidate(
        CandidatePack.model_validate(
            {
                **base,
                "candidate_id": "cand-a",
                "matched_subreddit": "OpenAI",
                "post_id": "p1",
                "title": "a",
                "top_communities": ["r/OpenAI"],
                "intent_tags": ["避坑"],
                "evidence_quotes": [{"text": "Agents need an audit trail before enterprises trust them in production.", "community": "r/OpenAI", "permalink": "https://reddit.com/p1"}],
            }
        )
    )
    save_candidate(
        CandidatePack.model_validate(
            {
                **base,
                "candidate_id": "cand-b",
                "signal_id": "sig-b",
                "matched_subreddit": "cursor",
                "post_id": "p2",
                "title": "b",
                "top_communities": ["r/cursor"],
                "intent_tags": ["趋势变化"],
                "evidence_quotes": [
                    {"text": "Without an audit trail, teams cannot inspect what agents actually did.", "community": "r/cursor", "permalink": "https://reddit.com/p2"},
                    {"text": "Teams only trust enterprise agents once the audit trail is inspectable.", "community": "r/cursor", "permalink": "https://reddit.com/p2b"},
                ],
            }
        )
    )

    async def _fake_generate(draft):
        return seed_group_validation_draft(mod.get_candidates(["cand-a", "cand-b"]))

    monkeypatch.setattr(mod, "generate_card_content", _fake_generate)
    results = await mod.materialize_breakdown_drafts(limit=10)
    assert len(results) == 1
    assert results[0].status == "failed"
    assert "write_bar" in (results[0].reason or "")
