from __future__ import annotations

from app.services.hotpost.signal_skill_experiment import (
    build_eval_signal_draft,
    build_experiment_messages,
)
from app.services.hotpost.card_content_generator import load_card_content_rules


def _case() -> dict:
    return {
        "eval_case_id": "signal-eval-case-1",
        "input_bundle": {
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "topic_pack_id": "paid-economics",
            "signal_level": "rising",
            "why_now_reason": "recurring_7d",
            "intent_tags": ["明确阻塞 / 吐槽到影响行动"],
            "thread_count": 2,
            "community_count": 1,
            "quote_count": 2,
            "source_communities": ["r/artificial"],
            "evidence_quotes": [
                {"text": "This silently fails in production.", "community": "r/artificial", "permalink": "https://reddit.com/a"}
            ],
        },
        "baseline_output": {"title": "旧标题"},
    }


def test_build_eval_signal_draft_reconstructs_minimal_input() -> None:
    draft = build_eval_signal_draft(_case(), variant_id="baseline_v1")
    assert draft.source_scope_id == "ai-automation"
    assert draft.topic_pack_id == "paid-economics"
    assert draft.matched_subreddit == "artificial"
    assert draft.time_window == "7d"
    assert draft.detail.min_test_action == ""


def test_experiment_messages_use_semantic_readout_contract() -> None:
    draft = build_eval_signal_draft(_case(), variant_id="human_summary_v1")
    messages = build_experiment_messages(
        draft,
        variant_id="human_summary_v1",
        banned_patterns=["越来越多人"],
        rules=load_card_content_rules(),
    )
    assert "R站资深专家" in messages[0]["content"]
    assert "不是那种坐在办公室里写报告的分析师" in messages[0]["content"]
    assert "千万别用" in messages[0]["content"]
    assert "潜力快帖只交付一个清楚变化" in messages[0]["content"]


def test_clean_quotes_variant_drops_low_value_bot_like_quote() -> None:
    case = _case()
    case["input_bundle"]["evidence_quotes"].append(
        {"text": "Hi, hit me up if you ever want to chat", "community": "r/artificial", "permalink": "https://reddit.com/b"}
    )
    draft = build_eval_signal_draft(case, variant_id="human_summary_tight_why_now_clean_quotes_v2")
    assert len(draft.evidence_quotes) == 1


def test_judgment_forward_strict_variant_uses_shared_semantic_contract() -> None:
    draft = build_eval_signal_draft(_case(), variant_id="judgment_forward_summary_strict_v2")
    messages = build_experiment_messages(
        draft,
        variant_id="judgment_forward_summary_strict_v2",
        banned_patterns=["越来越多人"],
        rules=load_card_content_rules(),
    )
    assert "summary_line：先总结你的判断" in messages[0]["content"]
    assert "只看帖子里有的证据" in messages[0]["content"]
    assert "别看到一个帖子就硬吹成行业趋势" in messages[0]["content"]


def test_paid_econ_variant_focuses_on_operator_decision() -> None:
    draft = build_eval_signal_draft(_case(), variant_id="paid_econ_decision_v1")
    messages = build_experiment_messages(
        draft,
        variant_id="paid_econ_decision_v1",
        banned_patterns=["越来越多人"],
        rules=load_card_content_rules(),
    )
    assert "这是投放经济信号" in messages[0]["content"]
    assert "先写投手要重新判断的动作" in messages[0]["content"]


def test_paid_econ_signal_readout_variant_forbids_report_ticket_title() -> None:
    draft = build_eval_signal_draft(_case(), variant_id="paid_econ_signal_readout_v2")
    messages = build_experiment_messages(
        draft,
        variant_id="paid_econ_signal_readout_v2",
        banned_patterns=["越来越多人"],
        rules=load_card_content_rules(),
    )
    assert "不要把后台词顶在最前面" in messages[0]["content"]
    assert "预算、回传、目标设置或出价判断" in messages[0]["content"]


def test_tools_efficiency_variant_keeps_shared_contract_without_pack_leakage() -> None:
    case = _case()
    case["input_bundle"]["topic_pack_id"] = "agent-builder"
    draft = build_eval_signal_draft(case, variant_id="tools_efficiency_focus_v1")
    messages = build_experiment_messages(
        draft,
        variant_id="tools_efficiency_focus_v1",
        banned_patterns=["越来越多人"],
        rules=load_card_content_rules(),
    )
    assert "这是 AI agent / 开发者工具信号" in messages[0]["content"]
    assert "真实落地门槛" in messages[0]["content"]


def test_tools_efficiency_strict_variant_uses_shared_contract_without_old_copy() -> None:
    case = _case()
    case["input_bundle"]["topic_pack_id"] = "agent-builder"
    draft = build_eval_signal_draft(case, variant_id="tools_efficiency_focus_strict_v1")
    messages = build_experiment_messages(
        draft,
        variant_id="tools_efficiency_focus_strict_v1",
        banned_patterns=["越来越多人"],
        rules=load_card_content_rules(),
    )
    assert "只讲证据里出现的成本、维护、审核、上下文或安全边界" in messages[0]["content"]
    assert "不要重复原帖标题" not in messages[0]["content"]
