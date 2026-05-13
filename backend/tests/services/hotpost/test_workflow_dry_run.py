from __future__ import annotations

import pytest

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_card_drafts import WritingCardDraft
from app.schemas.hotpost_card_review import BreakdownDraftMaterializeResult
from app.schemas.hotpost_source_scopes import SourceScope


@pytest.mark.asyncio
async def test_run_hotpost_workflow_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hotpost import workflow_dry_run as mod

    monkeypatch.setattr(
        mod,
        "list_source_scopes",
        lambda: [
            SourceScope(
                source_scope_id="ai-automation",
                title="AI 与自动化",
                description="test scope",
                subreddits=["OpenAI"],
                search_queries=["agent"],
                topic_packs=[],
            )
        ],
    )
    monkeypatch.setattr(mod, "collect_scope_candidates", _fake_collect)
    monkeypatch.setattr(mod, "list_candidates", lambda: [_fake_candidate()])
    monkeypatch.setattr(mod, "materialize_breakdown_drafts", _fake_materialize)
    monkeypatch.setattr(mod, "list_drafts", lambda card_type=None: [_fake_write_draft()])
    monkeypatch.setattr(mod, "audit_breakdown_overlap", lambda: {"pair_count": 2, "pairs": []})
    monkeypatch.setattr(mod, "load_published_cards", lambda: [])

    result = await mod.run_hotpost_workflow_dry_run(max_candidates=6, queue_limit=3)
    assert result["run_parameters"]["max_candidates_per_scope"] == 6
    assert result["operation_targets"]["min_cards_per_run"] == 15
    assert result["collect_results"] == {"ai-automation": 1}
    assert result["throughput"]["collected_total"] == 1
    assert result["validate_queue_summary"]["lane_counts"] == {"signal": 1}
    assert result["breakdown_materialize"]["materialized"] == 1
    assert result["overlap_pair_count"] == 2
    assert result["signal_queue"][0]["candidate_id"] == "cand-1"
    assert result["write_queue"][0]["draft_id"] == "draft-1"


async def _fake_collect(scope_id: str, max_candidates: int = 8, mode: str = "harvest"):
    return [_fake_candidate()]


async def _fake_materialize(limit: int = 20):
    return [
        BreakdownDraftMaterializeResult(
            suggestion_id="s-1",
            status="materialized",
            draft_id="draft-1",
            card_id="draft-1",
        )
    ]


def _fake_candidate() -> CandidatePack:
    return CandidatePack.model_validate(
        {
            "candidate_id": "cand-1",
            "signal_id": "sig-1",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "topic_pack_id": "agent-builder",
            "query": "agent audit trail",
            "matched_subreddit": "OpenAI",
            "post_id": "p1",
            "title": "Agents need audit trails",
            "score": 10,
            "num_comments": 5,
            "created_at": "2026-04-08T00:00:00Z",
            "collected_at": "2026-04-08T00:00:00Z",
            "collect_batch_id": "batch-1",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "recurring_7d",
            "listing_source": "search",
            "primary_reason": "test",
            "matched_keywords": ["agent audit trail"],
            "top_communities": ["r/OpenAI"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 1,
            "intent_tags": ["避坑"],
            "evidence_quotes": [{"text": "audit trails matter", "community": "r/OpenAI", "permalink": "https://reddit.com/p1"}],
        }
    )


def _fake_write_draft() -> WritingCardDraft:
    return WritingCardDraft.model_validate(
        {
            "draft_id": "draft-1",
            "candidate_id": "cand-1",
            "card_type": "write",
            "signal_id": "sig-1",
            "card_id": "card-draft-1",
            "candidate_ids": ["cand-1", "cand-2"],
            "category_id": "quality",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "matched_subreddit": "OpenAI",
            "post_id": "p1",
            "title": "Agent 落地最卡的不是功能，而是审计链",
            "score": 12,
            "num_comments": 6,
            "summary_line": "summary",
            "audience": "在试 agent 落地的开发者",
            "why_now": "why_now",
            "why_now_reason": "recurring_7d",
            "signal_level": "rising",
            "time_window": "7d",
            "intent_tags": ["避坑"],
            "thread_count": 2,
            "community_count": 2,
            "quote_count": 2,
            "evidence_quotes": [
                {"text": "q1", "community": "r/OpenAI", "permalink": "https://reddit.com/p1"},
                {"text": "q2", "community": "r/OpenAI", "permalink": "https://reddit.com/p2"},
            ],
            "source_link": "https://reddit.com/p1",
            "source_links": ["https://reddit.com/p1", "https://reddit.com/p2"],
            "source_communities": ["r/OpenAI", "r/cursor"],
            "detail": {
                "thesis": "audit trail 才是 enterprise agent 的落地门槛",
                "writing_angle_or_perspective": "",
                "tension_point_or_why_it_matters": "",
                "title_hooks": [],
                "quote_pack": [],
            },
        }
    )
