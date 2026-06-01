from __future__ import annotations

import asyncio

import pytest

from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost import card_content_generator as mod
from app.services.hotpost.card_draft_builder import seed_validation_draft


def _candidate() -> CandidatePack:
    return CandidatePack.model_validate(
        {
            "candidate_id": "cand-precheck-001",
            "signal_id": "sig-precheck-001",
            "source_scope_id": "business-growth-ops",
            "source_scope_name": "商业增长与运营",
            "topic_pack_id": "paid-economics",
            "query": "lead quality",
            "matched_subreddit": "PPC",
            "post_id": "ppc-precheck-001",
            "title": "Lead quality dropped after changing conversion goal",
            "score": 42,
            "num_comments": 13,
            "created_at": "2026-04-08T00:00:00Z",
            "collected_at": "2026-04-08T00:00:00Z",
            "collect_batch_id": "batch-1",
            "time_window": "7d",
            "signal_level": "sustained",
            "why_now_reason": "switch_signal_7d",
            "listing_source": "search",
            "primary_reason": "paid-economics:problem_keyword",
            "matched_keywords": ["lead quality"],
            "top_communities": ["r/PPC"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 1,
            "intent_tags": ["求建议"],
            "evidence_quotes": [
                {
                    "text": "Lead quality cratered after we changed the primary conversion goal.",
                    "community": "r/PPC",
                    "permalink": "https://www.reddit.com/r/PPC/comments/ppc-precheck-001/q1",
                }
            ],
        }
    )


@pytest.mark.asyncio
async def test_generate_draft_precheck_returns_report_only_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft = seed_validation_draft(_candidate())
    captured: dict[str, object] = {}

    async def _fake_generate_json(**kwargs):
        captured.update(kwargs)
        return {
            "decision": "PASS",
            "reasons": ["证据支撑当前主张"],
            "required_fixes": [],
            "risk_flags": [],
            "publish_note": "可以进入人工 review",
        }

    monkeypatch.setattr(mod, "_generate_json", _fake_generate_json)

    result = await mod._generate_draft_precheck(
        draft,
        semantic_brief={"publish_risk": "pass"},
        model="deepseek/deepseek-v4-pro",
        timeout=30.0,
        client_factory=lambda _model, _timeout: object(),
    )

    assert result["decision"] == "PASS"
    assert captured["stage"] == "draft_precheck"


@pytest.mark.asyncio
async def test_generate_draft_precheck_report_keeps_draft_when_precheck_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft = seed_validation_draft(_candidate())

    async def _fake_generate_json(**_kwargs):
        raise TimeoutError("precheck timeout")

    monkeypatch.setattr(mod, "_generate_json", _fake_generate_json)

    result = await mod._generate_draft_precheck_report(
        draft,
        semantic_brief={"publish_risk": "needs_human_review"},
        model="deepseek/deepseek-v4-pro",
        timeout=30.0,
        client_factory=lambda _model, _timeout: object(),
    )

    assert result["decision"] == "REWRITE"
    assert "precheck_error" in result["risk_flags"]
    assert result["should_block"] is False


@pytest.mark.asyncio
async def test_generate_draft_precheck_report_turns_stage_timeout_into_rewrite() -> None:
    draft = seed_validation_draft(_candidate())

    class SlowClient:
        async def generate(self, *_args, **_kwargs) -> str:
            await asyncio.sleep(0.05)
            return '{"decision":"PASS","reasons":[],"required_fixes":[],"risk_flags":[],"publish_note":"","should_rewrite":false,"should_block":false}'

    result = await mod._generate_draft_precheck_report(
        draft,
        semantic_brief={"publish_risk": "needs_human_review"},
        model="deepseek/deepseek-v4-pro",
        timeout=0.01,
        client_factory=lambda _model, _timeout: SlowClient(),
    )

    assert result["decision"] == "REWRITE"
    assert "precheck_error" in result["risk_flags"]
    assert "stage_timeout" in result["risk_flags"]
    assert result["should_block"] is False
