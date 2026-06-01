from __future__ import annotations

import pytest

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_card_drafts import ValidationCardDraft
from app.services.hotpost import review_card_ops as mod


def _candidate() -> CandidatePack:
    return CandidatePack.model_validate(
        {
            "candidate_id": "cand-ops-001",
            "signal_id": "sig-ops-001",
            "source_scope_id": "business-growth-ops",
            "source_scope_name": "商业增长与运营",
            "topic_pack_id": "paid-economics",
            "query": "blended cac",
            "matched_subreddit": "PPC",
            "post_id": "ppc123",
            "title": "Lead Quality + Primary Goal Changes?",
            "score": 10,
            "num_comments": 5,
            "created_at": "2026-04-08T00:00:00Z",
            "collected_at": "2026-04-08T00:00:00Z",
            "collect_batch_id": "batch-1",
            "time_window": "7d",
            "signal_level": "sustained",
            "why_now_reason": "switch_signal_7d",
            "listing_source": "search",
            "primary_reason": "paid-economics:problem_keyword",
            "matched_keywords": ["blended cac"],
            "top_communities": ["r/PPC"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 1,
            "intent_tags": ["求推荐"],
            "evidence_quotes": [
                {
                    "text": "A ROAS drop from 7x to 2x after switching offline conversions to primary is a specific signal.",
                    "community": "r/PPC",
                    "permalink": "https://www.reddit.com/r/PPC/comments/ppc123/q1",
                }
            ],
        }
    )


@pytest.mark.asyncio
async def test_seed_review_draft_generates_before_save(monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = _candidate()
    generated = ValidationCardDraft.model_validate(
        {
            **mod.seed_validation_draft(candidate).model_dump(mode="json"),
            "title": "把线下成交改成主要优化目标后，ROAS 一下从 7 倍掉到 2 倍。",
            "summary_line": "投手发现，把线下成交当成主要优化目标后，表现不只下滑，而且样本太少，系统一下学不稳。",
            "audience": "在广告后台反复调目标的投手",
            "why_now": "讨论已经不在争参数怎么填，而是在追问钱是不是被系统学偏了。",
        }
    )
    saved: list[ValidationCardDraft] = []

    async def _fake_generate(_draft: ValidationCardDraft, **_kwargs) -> ValidationCardDraft:
        return generated

    monkeypatch.setattr(mod, "get_candidate", lambda _candidate_id: candidate)
    monkeypatch.setattr(mod, "generate_card_content", _fake_generate)
    monkeypatch.setattr(mod, "save_generation_trace", lambda *args, **kwargs: None)
    monkeypatch.setattr(mod, "save_draft", lambda draft: saved.append(draft) or draft)

    result = await mod.seed_review_draft("cand-ops-001", "validate")

    assert result.title == generated.title
    assert saved[0].title == generated.title


@pytest.mark.asyncio
async def test_seed_review_draft_replaces_incomplete_existing_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = _candidate()
    existing = mod.seed_validation_draft(candidate)
    generated = ValidationCardDraft.model_validate(
        {
            **existing.model_dump(mode="json"),
            "title": "把线下成交改成主要优化目标后，ROAS 一下从 7 倍掉到 2 倍。",
            "summary_line": "投手发现，把线下成交当成主要优化目标后，表现不只下滑，而且样本太少，系统一下学不稳。",
            "audience": "在广告后台反复调目标的投手",
            "why_now": "讨论已经不在争参数怎么填，而是在追问钱是不是被系统学偏了。",
            "detail": {
                "pain_point": "回传样本太薄，系统学不稳。",
                "target_user_and_scene": "重度依赖线下成交回传的投手。",
                "why_test_now": "已经不只是掉量，而是优化目标本身被怀疑。",
                "min_test_action": "先复核最近 7 天的主目标切换前后样本量。",
                "continue_signal": "更多投手开始回退目标或拆 campaign。",
                "stop_signal": "回退后表现迅速恢复，说明不是独立信号。",
            },
        }
    )
    updated: list[ValidationCardDraft] = []
    saved: list[ValidationCardDraft] = []

    async def _fake_generate(_draft: ValidationCardDraft, **_kwargs) -> ValidationCardDraft:
        return generated

    monkeypatch.setattr(mod, "generate_card_content", _fake_generate)
    monkeypatch.setattr(mod, "save_generation_trace", lambda *args, **kwargs: None)
    monkeypatch.setattr(mod, "list_drafts", lambda *args, **kwargs: [existing])
    monkeypatch.setattr(mod, "save_draft", lambda draft: saved.append(draft) or draft)
    monkeypatch.setattr(mod, "update_draft", lambda draft_id, draft: updated.append(draft) or draft)

    result = await mod.seed_review_draft_from_candidate(candidate, "validate")

    assert result.title == generated.title
    assert saved == []
    assert updated[0].title == generated.title
