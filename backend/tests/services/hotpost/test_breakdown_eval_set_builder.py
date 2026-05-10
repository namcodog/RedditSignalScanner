from __future__ import annotations

import pytest

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_card_drafts import WritingCardDraft
from app.schemas.hotpost_card_review import BreakdownSuggestion
from app.services.hotpost.breakdown_eval_set_builder import build_breakdown_eval_artifacts


def _candidate(candidate_id: str, scope_id: str, pack_id: str) -> CandidatePack:
    return CandidatePack.model_validate(
        {
            "candidate_id": candidate_id,
            "signal_id": f"sig-{candidate_id}",
            "source_scope_id": scope_id,
            "source_scope_name": scope_id,
            "topic_pack_id": pack_id,
            "query": pack_id,
            "matched_subreddit": "OpenAI",
            "post_id": f"post-{candidate_id}",
            "title": f"title-{candidate_id}",
            "score": 10,
            "num_comments": 5,
            "created_at": "2026-04-08T00:00:00Z",
            "collected_at": "2026-04-08T00:10:00Z",
            "collect_batch_id": "batch-1",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "recurring_7d",
            "listing_source": "listing_top",
            "primary_reason": "test",
            "matched_keywords": [pack_id],
            "top_communities": ["r/OpenAI"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 2,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [
                {"text": f"quote-{candidate_id}-1", "community": "r/OpenAI", "permalink": f"https://reddit.com/{candidate_id}/1"},
                {"text": f"quote-{candidate_id}-2", "community": "r/OpenAI", "permalink": f"https://reddit.com/{candidate_id}/2"},
            ],
        }
    )


def _writing_draft(draft_id: str, candidate_ids: list[str], scope_id: str = "ai-automation") -> WritingCardDraft:
    return WritingCardDraft.model_validate(
        {
            "draft_id": draft_id,
            "candidate_id": draft_id.replace("draft-", ""),
            "candidate_ids": candidate_ids,
            "card_id": draft_id.replace("draft-", "card-"),
            "signal_id": draft_id.replace("draft-", "sig-"),
            "card_type": "write",
            "category_id": "write",
            "title": "title",
            "source_scope_id": scope_id,
            "source_scope_name": scope_id,
            "matched_subreddit": "OpenAI",
            "post_id": "post-1",
            "source_event_at": "2026-04-08T00:00:00Z",
            "score": 15,
            "num_comments": 8,
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "recurring_7d",
            "thread_count": max(len(candidate_ids), 2),
            "community_count": 2,
            "quote_count": 2,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [
                {"text": "quote-a", "community": "r/OpenAI", "permalink": "https://reddit.com/a"},
                {"text": "quote-b", "community": "r/OpenAI", "permalink": "https://reddit.com/b"},
            ],
            "summary_line": "summary",
            "audience": "谁在聊",
            "why_now": "why now",
            "source_link": "https://reddit.com/a",
            "source_links": ["https://reddit.com/a", "https://reddit.com/b"],
            "source_communities": ["r/OpenAI", "r/ClaudeAI"],
            "detail": {
                "thesis": "thesis",
                "writing_angle_or_perspective": "angle",
                "tension_point_or_why_it_matters": "tension",
                "title_hooks": [],
                "quote_pack": ["quote1", "quote2"],
            },
        }
    )


@pytest.mark.asyncio
async def test_build_breakdown_eval_artifacts_prefers_suggestions_and_published(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hotpost import breakdown_eval_set_builder as mod

    suggestion = BreakdownSuggestion(
        suggestion_id="suggestion-ai-1",
        source_scope_id="ai-automation",
        topic_pack_id="agent-builder",
        candidate_ids=["cand-a", "cand-b"],
        thread_count=2,
        community_count=2,
        intent_tags=["趋势变化"],
        evidence_score=4,
        hypothesis="tool calling unreliable",
        reason_codes=["shared_object"],
    )
    monkeypatch.setattr(mod, "list_breakdown_suggestions", lambda limit=50: [suggestion])
    monkeypatch.setattr(mod, "list_drafts", lambda card_type=None: [_writing_draft("draft-group-ai", ["cand-a", "cand-b"])])
    monkeypatch.setattr(
        mod,
        "load_cards_payload",
        lambda: {
            "published": [
                {
                    "card_id": "card-pub-1",
                    "card_type": "write",
                    "source_scope_id": "business-growth-ops",
                    "source_scope_name": "增长",
                    "topic_pack_id": None,
                    "intent_tags": ["趋势变化"],
                    "title": "published title",
                    "summary_line": "published summary",
                    "audience": "published audience",
                    "why_now": "published why now",
                    "detail": {"thesis": "t", "writing_angle_or_perspective": "a", "tension_point_or_why_it_matters": "b", "title_hooks": [], "quote_pack": ["q1", "q2"]},
                    "source_module": {"primary_communities": ["r/PPC"], "top_community": "r/PPC", "thread_count": 2, "community_count": 2, "last_active_text": "近7天", "tone_tags": []},
                    "preview_quote": {"text": "q1", "community": "r/PPC", "permalink": "https://reddit.com/q1"},
                    "quotes": [{"text": "q1", "community": "r/PPC", "permalink": "https://reddit.com/q1"}],
                }
            ]
        },
    )

    artifacts = await build_breakdown_eval_artifacts(target_real=2, target_synthetic=2)

    assert len(artifacts["real_cases"]) == 2
    assert artifacts["real_cases"][0]["sample_origin"] == "suggestion_write"
    assert artifacts["real_cases"][0]["input_bundle"]["topic_pack_id"] == "agent-builder"
    assert artifacts["real_cases"][1]["sample_origin"] == "published_write"
    assert len(artifacts["labels"]) == 2
    assert len(artifacts["synthetic_plan"]) == 2
    assert artifacts["labels"][0]["field_passes"]["thesis"] is None


@pytest.mark.asyncio
async def test_build_breakdown_eval_artifacts_records_generation_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hotpost import breakdown_eval_set_builder as mod

    suggestion = BreakdownSuggestion(
        suggestion_id="suggestion-sel-1",
        source_scope_id="ecommerce-sellers",
        topic_pack_id="selection-signals",
        candidate_ids=["cand-1", "cand-2"],
        thread_count=2,
        community_count=2,
        intent_tags=["替换"],
        evidence_score=5,
        hypothesis="can't find a better one",
        reason_codes=["shared_object"],
    )
    monkeypatch.setattr(mod, "list_breakdown_suggestions", lambda limit=50: [suggestion])
    monkeypatch.setattr(mod, "list_drafts", lambda card_type=None: [])
    monkeypatch.setattr(mod, "load_cards_payload", lambda: {"published": []})
    monkeypatch.setattr(mod, "get_candidates", lambda ids: [_candidate(ids[0], "ecommerce-sellers", "selection-signals"), _candidate(ids[1], "ecommerce-sellers", "selection-signals")])

    async def flaky_generator(draft: WritingCardDraft) -> WritingCardDraft:
        raise ValueError("write draft generation failed")

    artifacts = await build_breakdown_eval_artifacts(target_real=1, target_synthetic=0, generator=flaky_generator)

    assert artifacts["real_cases"] == []
    assert artifacts["generation_failures"] == [{"suggestion_id": "suggestion-sel-1", "error": "write draft generation failed"}]
