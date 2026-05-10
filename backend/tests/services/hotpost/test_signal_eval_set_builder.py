from __future__ import annotations

import pytest

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_card_drafts import ValidationCardDraft
from app.services.hotpost.signal_eval_set_builder import _select_candidates, build_signal_eval_artifacts


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
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 2,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [{"text": f"quote-{candidate_id}", "community": "r/OpenAI", "permalink": f"https://reddit.com/{candidate_id}"}],
        }
    )


async def _fake_generator(draft: ValidationCardDraft) -> ValidationCardDraft:
    return draft.model_copy(update={"summary_line": "baseline summary", "audience": "真实在聊的人", "why_now": "这波值得继续盯。", "detail": {"pain_point": "痛点", "target_user_and_scene": "场景", "why_test_now": "理由", "min_test_action": "去看原始讨论", "continue_signal": "继续盯", "stop_signal": "先放过"}})


@pytest.mark.asyncio
async def test_build_signal_eval_artifacts_mixes_published_and_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hotpost import signal_eval_set_builder as mod

    monkeypatch.setattr(
        mod,
        "load_cards_payload",
        lambda: {
            "published": [
                {
                    "card_id": "card-1",
                    "card_type": "validate",
                    "source_scope_id": "ai-automation",
                    "source_scope_name": "AI",
                    "signal_level": "hot",
                    "why_now_reason": "new_threads_24h",
                    "intent_tags": ["趋势变化"],
                    "title": "title",
                    "summary_line": "summary",
                    "audience": "谁在聊",
                    "why_now": "为什么要看",
                    "detail": {"pain_point": "a", "target_user_and_scene": "b", "why_test_now": "c", "min_test_action": "去看原始讨论", "continue_signal": "d", "stop_signal": "e"},
                    "source_module": {"primary_communities": ["r/OpenAI"], "top_community": "r/OpenAI", "thread_count": 1, "community_count": 1, "last_active_text": "近24小时", "tone_tags": []},
                    "preview_quote": {"text": "q", "community": "r/OpenAI", "permalink": "https://reddit.com/q"},
                    "quotes": [{"text": "q", "community": "r/OpenAI", "permalink": "https://reddit.com/q"}],
                }
            ],
            "candidates": [
                _candidate("cand-1", "ai-automation", "agent-builder").model_dump(mode="json"),
                _candidate("cand-2", "ecommerce-sellers", "selection-signals").model_dump(mode="json"),
            ],
        },
    )

    artifacts = await build_signal_eval_artifacts(target_real=3, target_synthetic=2, generator=_fake_generator)

    assert len(artifacts["real_cases"]) == 3
    assert len(artifacts["labels"]) == 3
    assert len(artifacts["synthetic_plan"]) == 2
    assert artifacts["real_cases"][0]["sample_origin"] == "published_validate"
    assert artifacts["real_cases"][1]["sample_origin"] == "candidate_generated"
    assert artifacts["real_cases"][0]["eval_case_id"].startswith("signal-eval-published-")
    assert artifacts["real_cases"][1]["eval_case_id"].startswith("signal-eval-generated-")
    assert artifacts["labels"][0]["review_status"] == "pending"


@pytest.mark.asyncio
async def test_build_signal_eval_artifacts_skips_generation_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hotpost import signal_eval_set_builder as mod

    monkeypatch.setattr(mod, "load_cards_payload", lambda: {"published": [], "candidates": [_candidate("cand-1", "ai-automation", "agent-builder").model_dump(mode="json"), _candidate("cand-2", "ai-automation", "agent-builder").model_dump(mode="json")]})

    async def flaky_generator(draft: ValidationCardDraft) -> ValidationCardDraft:
        if draft.candidate_id == "cand-1":
            raise ValueError("LLM returned invalid JSON")
        return await _fake_generator(draft)

    artifacts = await build_signal_eval_artifacts(target_real=1, target_synthetic=0, generator=flaky_generator)

    assert len(artifacts["real_cases"]) == 1
    assert artifacts["generation_failures"] == [{"candidate_id": "cand-1", "error": "LLM returned invalid JSON"}]


def test_select_candidates_deduplicates_same_candidate_id() -> None:
    candidate = _candidate("cand-dup", "ai-automation", "agent-builder")
    picked = _select_candidates([candidate, candidate], needed=5)
    assert len(picked) == 1
    assert picked[0].candidate_id == "cand-dup"
