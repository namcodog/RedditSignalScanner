from __future__ import annotations

from backend.scripts.evals.run_hotpost_three_tab_prompt_ab_v4 import (
    SEMANTIC_MODEL,
    WRITER_MODEL,
    build_semantic_brief_messages,
    build_writer_messages,
    render_v4_markdown_report,
    with_v4_banned_patterns,
)


def test_v4_uses_requested_two_stage_models() -> None:
    assert SEMANTIC_MODEL == "google/gemini-3.1-pro-preview"
    assert WRITER_MODEL == "qwen/qwen3.6-max-preview"


def test_semantic_brief_prompt_focuses_on_english_interpretation() -> None:
    messages = build_semantic_brief_messages(
        lane="signal",
        card_id="card-1",
        published={"title": "旧标题"},
        baseline={"title": "A"},
        variant_v3={"title": "B"},
    )
    prompt = "\n".join(message["content"] for message in messages)

    assert "English Reddit evidence" in prompt
    assert "core_interpretation" in prompt
    assert "evidence_boundary" in prompt
    assert "field_guidance" in prompt
    assert "Do not write the final Chinese card" in prompt


def test_writer_messages_inject_semantic_brief_and_qwen_role() -> None:
    messages = [{"role": "system", "content": "base system"}, {"role": "user", "content": "{}"}]
    brief = {
        "core_interpretation": "用户不再只看提示词，而是看真实数据接入。",
        "evidence_boundary": "只能说这个讨论里有人开始这么判断。",
        "field_guidance": {"title": "标题要说清数据接入。"},
    }

    writer_messages = build_writer_messages(messages, semantic_brief=brief)

    assert writer_messages[0]["content"].startswith("base system")
    assert "Gemini semantic brief" in writer_messages[0]["content"]
    assert "用户不再只看提示词" in writer_messages[0]["content"]
    assert "中文字段" in writer_messages[0]["content"]
    assert writer_messages[1] == messages[1]


def test_v4_report_uses_two_stage_title() -> None:
    report = render_v4_markdown_report(
        [
            {
                "lane": "signal",
                "card_id": "signal-1",
                "model": "google/gemini-3.1-pro-preview -> qwen/qwen3.6-max-preview",
                "baseline": {"title": "旧标题"},
                "variant": {"title": "新标题"},
            }
        ]
    )

    assert "# Hotpost 三 Tab Prompt A/B v4 two-stage 小样本报告" in report
    assert "google/gemini-3.1-pro-preview -> qwen/qwen3.6-max-preview" in report


def test_v4_banned_patterns_include_v3_without_mutating_rules() -> None:
    rules = {"banned_patterns": {"global": ["existing"]}}

    patched = with_v4_banned_patterns(rules)

    assert "existing" in patched["banned_patterns"]["global"]
    assert "判断顺序从" in patched["banned_patterns"]["global"]
    assert "这帖现在值得看" in patched["banned_patterns"]["global"]
    assert rules["banned_patterns"]["global"] == ["existing"]
