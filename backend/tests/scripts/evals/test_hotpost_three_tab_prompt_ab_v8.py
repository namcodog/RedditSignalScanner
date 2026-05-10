from __future__ import annotations

from backend.scripts.evals.run_hotpost_three_tab_prompt_ab_v8 import (
    SEMANTIC_MODEL,
    WRITER_MODEL,
    render_v8_markdown_report,
    write_outputs,
)


def test_v8_uses_gemini_flash_and_mimo_25_pro() -> None:
    assert SEMANTIC_MODEL == "google/gemini-3-flash-preview"
    assert WRITER_MODEL == "xiaomi/mimo-v2.5-pro"


def test_v8_report_uses_distinct_title_and_model_route() -> None:
    report = render_v8_markdown_report(
        [
            {
                "lane": "signal",
                "card_id": "signal-1",
                "model": "google/gemini-3-flash-preview -> xiaomi/mimo-v2.5-pro",
                "baseline": {"title": "旧标题"},
                "variant": {"title": "新标题"},
            }
        ]
    )

    assert "# Hotpost 三 Tab Prompt A/B v8 flash-mimo25 小样本报告" in report
    assert "google/gemini-3-flash-preview -> xiaomi/mimo-v2.5-pro" in report


def test_v8_writes_distinct_artifacts(tmp_path, monkeypatch) -> None:
    from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v8 as v8

    monkeypatch.setattr(v8, "REPORTS_EVALS_DIR", tmp_path)

    json_path, md_path = write_outputs([])

    assert json_path.name == "hotpost_three_tab_prompt_ab_v8_flash_mimo25_results.json"
    assert md_path.name == "hotpost_three_tab_prompt_ab_v8_flash_mimo25_report.md"
    assert json_path.exists()
    assert md_path.exists()
