from __future__ import annotations

import pytest

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_card_drafts import ValidationCardDraft
from app.services.hotpost.signal_pack_eval_builder import build_signal_pack_eval_cases


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
            "created_at": "2026-04-07T00:00:00Z",
            "collected_at": "2026-04-07T00:10:00Z",
            "collect_batch_id": "batch-1",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "recurring_7d",
            "listing_source": "listing_top",
            "primary_reason": "test",
            "matched_keywords": [pack_id],
            "top_communities": ["r/OpenAI"],
            "thread_count": 2,
            "community_count": 1,
            "quote_count": 2,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [{"text": f"quote-{candidate_id}", "community": "r/OpenAI", "permalink": f"https://reddit.com/{candidate_id}"}],
        }
    )


async def _fake_generator(draft: ValidationCardDraft) -> ValidationCardDraft:
    return draft.model_copy(
        update={
            "summary_line": "baseline summary",
            "audience": "真实在聊的人",
            "why_now": "这波值得继续盯。",
            "detail": {
                "pain_point": "痛点",
                "target_user_and_scene": "场景",
                "why_test_now": "理由",
                "min_test_action": "去看原始讨论",
                "continue_signal": "继续盯",
                "stop_signal": "先放过",
            },
        }
    )


@pytest.mark.asyncio
async def test_build_signal_pack_eval_cases_filters_scope_and_pack(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hotpost import signal_pack_eval_builder as mod

    monkeypatch.setattr(
        mod,
        "load_cards_payload",
        lambda: {
            "published": [],
            "candidates": [
                _candidate("cand-1", "ai-automation", "tools-efficiency").model_dump(mode="json"),
                _candidate("cand-2", "ai-automation", "agent-builder").model_dump(mode="json"),
                _candidate("cand-3", "business-growth-ops", "paid-economics").model_dump(mode="json"),
            ],
        },
    )

    result = await build_signal_pack_eval_cases(
        source_scope_id="ai-automation",
        topic_pack_id="tools-efficiency",
        generator=_fake_generator,
    )

    assert result["case_count"] == 1
    assert result["cases"][0]["input_bundle"]["topic_pack_id"] == "tools-efficiency"
    assert result["generation_failure_count"] == 0


@pytest.mark.asyncio
async def test_build_signal_pack_eval_cases_records_generation_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hotpost import signal_pack_eval_builder as mod

    monkeypatch.setattr(
        mod,
        "load_cards_payload",
        lambda: {
            "published": [],
            "candidates": [
                _candidate("cand-1", "business-growth-ops", "paid-economics").model_dump(mode="json"),
                _candidate("cand-2", "business-growth-ops", "paid-economics").model_dump(mode="json"),
            ],
        },
    )

    async def flaky_generator(draft: ValidationCardDraft) -> ValidationCardDraft:
        if draft.candidate_id == "cand-1":
            raise ValueError("bad input")
        return await _fake_generator(draft)

    result = await build_signal_pack_eval_cases(
        source_scope_id="business-growth-ops",
        topic_pack_id="paid-economics",
        generator=flaky_generator,
    )

    assert result["case_count"] == 1
    assert result["generation_failures"] == [{"candidate_id": "cand-1", "error": "bad input"}]
