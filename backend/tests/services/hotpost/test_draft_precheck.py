from __future__ import annotations

import pytest

from app.services.hotpost.draft_precheck import (
    build_draft_precheck_messages,
    parse_draft_precheck_result,
)


def test_parse_precheck_pass() -> None:
    result = parse_draft_precheck_result(
        {
            "decision": "PASS",
            "reasons": ["证据和主张一致"],
            "required_fixes": [],
            "risk_flags": [],
            "publish_note": "可以进入人工 review",
        }
    )

    assert result["decision"] == "PASS"
    assert result["should_block"] is False


def test_parse_precheck_rewrite() -> None:
    result = parse_draft_precheck_result(
        {
            "decision": "REWRITE",
            "reasons": ["标题放大了证据"],
            "required_fixes": ["把标题降调"],
            "risk_flags": ["overclaim"],
            "publish_note": "先改稿再看",
        }
    )

    assert result["decision"] == "REWRITE"
    assert result["should_rewrite"] is True


def test_parse_precheck_forces_rewrite_for_weak_min_test_action() -> None:
    result = parse_draft_precheck_result(
        {
            "decision": "PASS",
            "reasons": [],
            "required_fixes": [],
            "risk_flags": [],
            "publish_note": "",
        },
        draft_payload={"detail": {"min_test_action": "去看原始讨论"}},
    )

    assert result["decision"] == "REWRITE"
    assert "weak_min_test_action" in result["risk_flags"]


def test_parse_precheck_forces_rewrite_for_truncated_quote() -> None:
    result = parse_draft_precheck_result(
        {
            "decision": "PASS",
            "reasons": [],
            "required_fixes": [],
            "risk_flags": [],
            "publish_note": "",
        },
        draft_payload={
            "detail": {
                "why_test_now": "原话里有个关键句：“You’re trying to play the middle man. You’re going to”。"
            }
        },
    )

    assert result["decision"] == "REWRITE"
    assert "truncated_quote" in result["risk_flags"]


def test_parse_precheck_forces_rewrite_for_junk_tracking_terms() -> None:
    result = parse_draft_precheck_result(
        {
            "decision": "PASS",
            "reasons": [],
            "required_fixes": [],
            "risk_flags": [],
            "publish_note": "",
        },
        draft_payload={
            "detail": {
                "continue_signal": "继续看 Please educate、years、old 这些词会不会继续出现。"
            }
        },
    )

    assert result["decision"] == "REWRITE"
    assert "junk_tracking_terms" in result["risk_flags"]


def test_parse_precheck_block() -> None:
    result = parse_draft_precheck_result(
        {
            "decision": "BLOCK",
            "reasons": ["证据不支撑当前主张"],
            "required_fixes": [],
            "risk_flags": ["unsupported_claim"],
            "publish_note": "不建议进入人工 review",
        }
    )

    assert result["decision"] == "BLOCK"
    assert result["should_block"] is True


def test_parse_precheck_rejects_unknown_decision() -> None:
    with pytest.raises(ValueError, match="invalid precheck decision"):
        parse_draft_precheck_result({"decision": "MAYBE"})


def test_build_precheck_messages_contains_draft_and_brief() -> None:
    messages = build_draft_precheck_messages(
        draft_payload={"title": "投手发现线索质量掉了", "card_type": "validate"},
        semantic_brief={"publish_risk": "needs_human_review"},
    )

    assert messages[0]["role"] == "system"
    assert "PASS / REWRITE / BLOCK" in messages[0]["content"]
    assert "去看原始讨论" in messages[0]["content"]
    assert "半截英文原话" in messages[0]["content"]
    assert "semantic_brief" in messages[1]["content"]
    assert "投手发现线索质量掉了" in messages[1]["content"]
