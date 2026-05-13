from __future__ import annotations

from app.services.hotpost.signal_polish_experiment import run_signal_polish_variant
from app.services.hotpost.signal_polish_variant_policy import apply_signal_polish_variant

import pytest


def test_apply_signal_polish_variant_cleans_summary_prefix_and_why_now() -> None:
    output = {
        "title": "问题：工具切换导致上下文丢失",
        "summary_line": "几条讨论都在说同一件事：工具一多以后，上下文总在来回搬，最后没人愿意坚持那套流程。",
        "audience": "使用多个工具的人",
        "why_now": "旧文案",
        "detail": {"why_test_now": "旧文案"},
    }
    polished = apply_signal_polish_variant(
        output,
        input_bundle={"intent_tags": ["避坑"], "why_now_reason": "recurring_7d"},
        variant_id="clean_summary_tight_why_now_polish_v1",
    )
    assert polished["summary_line"].startswith("工具一多以后")
    assert polished["title"] == "问题，工具切换导致上下文丢失"
    assert "吐槽变成避坑提醒" in polished["why_now"]
    assert polished["detail"]["why_test_now"] == "旧文案"
    assert polished["detail"]["why_test_now"] != polished["why_now"]


def test_apply_signal_polish_variant_growth_pack_softens_overclaim() -> None:
    output = {
        "title": "Reddit广告被直指80%+点击欺诈的最糟营销支出",
        "summary_line": "这意味着Reddit广告易陷80%+点击欺诈，成为绝对最差预算选择，从业者已开始重新评估其价值。",
        "audience": "投放者",
        "why_now": "旧文案",
        "detail": {"why_test_now": "旧文案"},
    }
    polished = apply_signal_polish_variant(
        output,
        input_bundle={"source_scope_id": "business-growth-ops", "intent_tags": [], "why_now_reason": "switch_signal_7d"},
        variant_id="clean_summary_growth_pack_polish_v3",
    )
    assert "最糟" not in polished["title"]
    assert "绝对最差预算选择" not in polished["summary_line"]
    assert polished["summary_line"].startswith("Reddit广告易陷80%+点击欺诈")


@pytest.mark.asyncio
async def test_run_signal_polish_variant_wraps_baseline_variant(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_signal_skill_variant(case, *, variant_id, model, timeout, rules, client_factory=None):
        assert variant_id == "human_summary_tight_why_now_v1"
        return {
            "eval_case_id": case["eval_case_id"],
            "variant_id": variant_id,
            "input_bundle": case["input_bundle"],
            "baseline_output": {
                "title": "标题：报告腔",
                "summary_line": "几条讨论都在说同一件事：这事开始影响判断。",
                "audience": "用户",
                "why_now": "旧文案",
                "detail": {"why_test_now": "旧文案"},
            },
        }

    monkeypatch.setattr(
        "app.services.hotpost.signal_polish_experiment.run_signal_skill_variant",
        fake_run_signal_skill_variant,
    )
    result = await run_signal_polish_variant(
        {
            "eval_case_id": "case-1",
            "input_bundle": {"intent_tags": [], "why_now_reason": "new_threads_24h"},
        },
        variant_id="clean_summary_polish_v1",
        model="fake-model",
        timeout=1.0,
        rules={"timeouts": {"signal_seconds": 1}},
    )
    assert result["variant_id"] == "clean_summary_polish_v1"
    assert result["baseline_output"]["summary_line"] == "这事开始影响判断。"
