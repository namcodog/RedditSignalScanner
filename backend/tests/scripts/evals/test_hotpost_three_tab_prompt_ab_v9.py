from __future__ import annotations

from backend.scripts.evals.run_hotpost_three_tab_prompt_ab_v9 import (
    SEMANTIC_MODEL,
    WRITER_MODEL,
    build_v9_writer_messages,
    generate_semantic_brief_once,
    render_v9_markdown_report,
    write_outputs,
)


def test_v9_uses_deepseek_v4_flash_and_mimo_25_pro() -> None:
    assert SEMANTIC_MODEL == "deepseek/deepseek-v4-flash"
    assert WRITER_MODEL == "xiaomi/mimo-v2.5-pro"


def test_v9_report_uses_distinct_title_and_model_route() -> None:
    report = render_v9_markdown_report(
        [
            {
                "lane": "signal",
                "card_id": "signal-1",
                "model": "deepseek/deepseek-v4-flash -> xiaomi/mimo-v2.5-pro",
                "baseline": {"title": "旧标题"},
                "variant": {"title": "新标题"},
            }
        ]
    )

    assert "# Hotpost 三 Tab Prompt A/B v9 deepseekflash-mimo25 小样本报告" in report
    assert "deepseek/deepseek-v4-flash -> xiaomi/mimo-v2.5-pro" in report


def test_v9_writes_distinct_artifacts(tmp_path, monkeypatch) -> None:
    from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v9 as v9

    monkeypatch.setattr(v9, "REPORTS_EVALS_DIR", tmp_path)

    json_path, md_path = write_outputs([])

    assert json_path.name == "hotpost_three_tab_prompt_ab_v9_deepseekflash_mimo25_results.json"
    assert md_path.name == "hotpost_three_tab_prompt_ab_v9_deepseekflash_mimo25_report.md"
    assert json_path.exists()
    assert md_path.exists()


async def test_v9_non_google_semantic_brief_uses_openrouter_without_response_format(monkeypatch) -> None:
    calls: list[dict] = []

    async def fake_generate_json_without_response_format(**kwargs):
        calls.append(kwargs)
        return {"core_interpretation": "英文证据说明用户担心成本。"}

    from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v9 as v9

    monkeypatch.setattr(v9.v5, "_generate_json_without_response_format", fake_generate_json_without_response_format)

    brief = await generate_semantic_brief_once(
        lane="signal",
        card_id="signal-1",
        published={"title": "old"},
        baseline={"title": "base"},
        variant_v3={"title": "base"},
        model="deepseek/deepseek-v4-flash",
    )

    assert brief == {"core_interpretation": "英文证据说明用户担心成本。"}
    assert calls[0]["model"] == "deepseek/deepseek-v4-flash"
    assert calls[0]["max_tokens"] == 4096


def test_v9_writer_prompt_does_not_call_deepseek_brief_gemini() -> None:
    messages = build_v9_writer_messages(
        [{"role": "system", "content": "base"}, {"role": "user", "content": "{}"}],
        semantic_brief={"core_interpretation": "中文理解"},
    )

    assert "Gemini semantic brief" not in messages[0]["content"]
    assert "语义理解层" in messages[0]["content"]
