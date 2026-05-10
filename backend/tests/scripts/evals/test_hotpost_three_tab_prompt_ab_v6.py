from __future__ import annotations

from backend.scripts.evals.run_hotpost_three_tab_prompt_ab_v6 import (
    SEMANTIC_MODEL,
    WRITER_MODEL,
    render_v6_markdown_report,
    write_outputs,
)


def test_v6_uses_gemini_flash_and_qwen() -> None:
    assert SEMANTIC_MODEL == "google/gemini-3-flash-preview"
    assert WRITER_MODEL == "qwen/qwen3.6-max-preview"


def test_v6_report_uses_distinct_title_and_model_route() -> None:
    report = render_v6_markdown_report(
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

    assert "# Hotpost 三 Tab Prompt A/B v6 flash-qwen 小样本报告" in report
    assert "google/gemini-3-flash-preview -> qwen/qwen3.6-max-preview" in report


def test_v6_writes_distinct_artifacts(tmp_path, monkeypatch) -> None:
    from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v6 as v6

    monkeypatch.setattr(v6, "REPORTS_EVALS_DIR", tmp_path)

    json_path, md_path = write_outputs([])

    assert json_path.name == "hotpost_three_tab_prompt_ab_v6_flash_qwen_results.json"
    assert md_path.name == "hotpost_three_tab_prompt_ab_v6_flash_qwen_report.md"
    assert json_path.exists()
    assert md_path.exists()
