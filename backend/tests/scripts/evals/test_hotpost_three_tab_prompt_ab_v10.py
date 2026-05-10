from __future__ import annotations

from backend.scripts.evals.run_hotpost_three_tab_prompt_ab_v10 import (
    SEMANTIC_MODEL,
    WRITER_MODEL,
    build_v10_semantic_brief_messages,
    load_v9_baseline_rows,
    render_v10_markdown_report,
    write_outputs,
)


def test_v10_keeps_v9_model_chain() -> None:
    assert SEMANTIC_MODEL == "deepseek/deepseek-v4-flash"
    assert WRITER_MODEL == "xiaomi/mimo-v2.5-pro"


def test_v10_semantic_prompt_adds_reddit_context_translation() -> None:
    messages = build_v10_semantic_brief_messages(
        lane="hot",
        card_id="card-1",
        published={"title": "old"},
        baseline={"title": "v9 input"},
        variant_v3={"title": "v9 input"},
    )

    system = messages[0]["content"]
    assert "reddit_context_translation" in system
    assert "jargon_or_meme_explainer" in system
    assert "sarcasm_or_tone" in system
    assert "plain_chinese_angle" in system
    assert "Do not translate literally" in system


def test_v10_report_uses_v9_as_baseline_title_and_route() -> None:
    report = render_v10_markdown_report(
        [
            {
                "lane": "signal",
                "card_id": "signal-1",
                "model": "v9 baseline vs v10 reddit-context",
                "baseline": {"title": "V9 标题"},
                "variant": {"title": "V10 标题"},
            }
        ]
    )

    assert "# Hotpost 三 Tab Prompt A/B v10 reddit-context 小样本报告" in report
    assert "A baseline: V9 标题" in report
    assert "B variant: V10 标题" in report
    assert "v9 baseline vs v10 reddit-context" in report


def test_v10_writes_distinct_artifacts(tmp_path, monkeypatch) -> None:
    from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v10 as v10

    monkeypatch.setattr(v10, "REPORTS_EVALS_DIR", tmp_path)

    json_path, md_path = write_outputs([])

    assert json_path.name == "hotpost_three_tab_prompt_ab_v10_reddit_context_results.json"
    assert md_path.name == "hotpost_three_tab_prompt_ab_v10_reddit_context_report.md"
    assert json_path.exists()
    assert md_path.exists()


def test_v10_loads_v9_variant_as_baseline(tmp_path) -> None:
    path = tmp_path / "v9.json"
    path.write_text(
        """
[
  {
    "card_id": "card-1",
    "baseline": {"title": "single stage"},
    "variant": {"title": "v9 title"},
    "semantic_brief": {"core_interpretation": "v9 brief"}
  }
]
""".strip(),
        encoding="utf-8",
    )

    rows = load_v9_baseline_rows(path)

    assert rows["card-1"]["variant"]["title"] == "v9 title"
    assert rows["card-1"]["baseline"]["title"] == "single stage"
