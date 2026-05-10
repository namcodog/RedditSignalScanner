from __future__ import annotations

import pytest

from backend.scripts.evals.run_hotpost_three_tab_prompt_ab_v7 import (
    SEMANTIC_MODEL,
    WRITER_MODEL,
    build_concise_writer_messages,
    build_v7_copy_repair_messages,
    find_v7_copy_issues,
    generate_semantic_brief_with_retry,
    merge_repaired_fields,
    render_v7_markdown_report,
    write_outputs,
)


def test_v7_uses_gemini_flash_and_qwen() -> None:
    assert SEMANTIC_MODEL == "google/gemini-3-flash-preview"
    assert WRITER_MODEL == "qwen/qwen3.6-max-preview"


def test_v7_writer_overlay_requires_short_accurate_one_glance_copy() -> None:
    messages = [{"role": "system", "content": "base system"}, {"role": "user", "content": "{}"}]

    writer_messages = build_concise_writer_messages(messages)

    content = writer_messages[0]["content"]
    assert content.startswith("base system")
    assert "一眼看懂" in content
    assert "更短" in content
    assert "不能为了短而丢掉关键意思" in content
    assert "保持原 JSON 字段和结构不变" in content
    assert writer_messages[1] == messages[1]


def test_v7_writer_overlay_blocks_english_fragments_outside_quote_pack() -> None:
    messages = [{"role": "system", "content": "base system"}, {"role": "user", "content": "{}"}]

    writer_messages = build_concise_writer_messages(messages)

    content = writer_messages[0]["content"]
    assert "quote_pack" in content
    assert "不要输出英文长句、截断英文引用" in content
    assert "continue_signal" in content
    assert "不能观察关键词" in content
    assert "不要写“原话里有个关键句”" in content


def test_v7_copy_issues_detect_report_tone_and_english_fragments() -> None:
    generated = {
        "why_test_now": "原话里有个关键句：“Yeah, same realization—LLMs work best as tools, not autonomous agents. Once you treat them l”。这说明问题很真实。",
        "continue_signal": "继续看 Agent、completely agree、and 这些词会不会继续出现。",
        "quote_pack": [
            "Yeah, same realization—LLMs work best as tools｜大家已经发现，大模型更适合当工具｜r/test"
        ],
    }

    issues = find_v7_copy_issues(generated)

    assert any("报告腔" in issue for issue in issues)
    assert any("英文长句" in issue for issue in issues)
    assert any("关键词观察" in issue for issue in issues)
    assert not any("quote_pack" in issue for issue in issues)


def test_v7_copy_repair_messages_are_clean_chinese_editing_pass() -> None:
    messages = build_v7_copy_repair_messages(
        generated={"title": "标题", "why_test_now": "原话里有个关键句：“This is sick”"},
        semantic_brief={"core_interpretation": "真实数据接入才是重点"},
        issues=["why_test_now: 报告腔或模板化表达 `原话里有个关键句`"],
    )

    content = messages[0]["content"]
    user_payload = messages[1]["content"]
    assert "中文质检改写" in content
    assert "不要引用或粘贴原始英文" in content
    assert "只输出 JSON" in content
    assert "完整 JSON" in content
    assert "required_fields" in user_payload
    assert '"title"' in user_payload
    assert '"why_test_now"' in user_payload
    assert "真实数据接入才是重点" in user_payload
    assert "原始英文长文" not in user_payload


def test_merge_repaired_fields_keeps_original_when_repair_omits_field() -> None:
    merged = merge_repaired_fields(
        original={"title": "原标题", "why_test_now": "原证据", "title_hooks": ["原 hook"]},
        repaired={"title": "新标题", "why_test_now": "", "extra": "不要"},
    )

    assert merged == {"title": "新标题", "why_test_now": "原证据", "title_hooks": ["原 hook"]}


def test_v7_report_uses_distinct_title_and_model_route() -> None:
    report = render_v7_markdown_report(
        [
            {
                "lane": "signal",
                "card_id": "signal-1",
                "model": "google/gemini-3-flash-preview -> qwen/qwen3.6-max-preview",
                "baseline": {"title": "旧标题"},
                "variant": {"title": "新标题"},
            }
        ]
    )

    assert "# Hotpost 三 Tab Prompt A/B v7 concise-qwen 小样本报告" in report
    assert "google/gemini-3-flash-preview -> qwen/qwen3.6-max-preview" in report


def test_v7_writes_distinct_artifacts(tmp_path, monkeypatch) -> None:
    from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v7 as v7

    monkeypatch.setattr(v7, "REPORTS_EVALS_DIR", tmp_path)

    json_path, md_path = write_outputs([])

    assert json_path.name == "hotpost_three_tab_prompt_ab_v7_concise_qwen_results.json"
    assert md_path.name == "hotpost_three_tab_prompt_ab_v7_concise_qwen_report.md"
    assert json_path.exists()
    assert md_path.exists()


@pytest.mark.asyncio
async def test_v7_retries_empty_semantic_brief(monkeypatch) -> None:
    from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v7 as v7

    attempts = 0

    async def fake_generate_semantic_brief(**kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ValueError("semantic brief is empty")
        return {"core_interpretation": "第二次返回成功"}

    monkeypatch.setattr(v7.v4, "generate_semantic_brief", fake_generate_semantic_brief)

    brief = await generate_semantic_brief_with_retry(
        lane="breakdown",
        card_id="card-1",
        published={},
        baseline={},
        variant_v3={},
        model=SEMANTIC_MODEL,
    )

    assert brief == {"core_interpretation": "第二次返回成功"}
    assert attempts == 2


@pytest.mark.asyncio
async def test_v7_retries_transient_semantic_client_error(monkeypatch) -> None:
    from app.services.llm.interfaces import LLMClientError
    from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v7 as v7

    attempts = 0

    async def fake_generate_semantic_brief(**kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise LLMClientError("gemini", "The read operation timed out")
        return {"core_interpretation": "第二次返回成功"}

    monkeypatch.setattr(v7.v4, "generate_semantic_brief", fake_generate_semantic_brief)

    brief = await generate_semantic_brief_with_retry(
        lane="breakdown",
        card_id="card-1",
        published={},
        baseline={},
        variant_v3={},
        model=SEMANTIC_MODEL,
    )

    assert brief == {"core_interpretation": "第二次返回成功"}
    assert attempts == 2
