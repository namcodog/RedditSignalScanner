from __future__ import annotations

from backend.scripts.evals.run_hotpost_three_tab_prompt_ab_v11 import (
    WRITER_MODEL,
    build_chinese_fluency_repair_messages,
    find_v11_fluency_issues,
    load_v10_baseline_rows,
    render_v11_markdown_report,
    write_outputs,
)


def test_v11_keeps_mimo_writer_for_chinese_fluency_repair() -> None:
    assert WRITER_MODEL == "xiaomi/mimo-v2.5-pro"


def test_v11_detects_dead_object_subject_human_action() -> None:
    issues = find_v11_fluency_issues(
        {
            "continue_signal": "后续看有没有更多用户分享类似的数据接入工作流，或者工具开始强调自己的数据连接功能。",
            "title": "AI 做 SEO，光写提示词不够",
        }
    )

    assert any("工具开始强调" in issue for issue in issues)


def test_v11_repair_prompt_blocks_dead_object_subjects() -> None:
    messages = build_chinese_fluency_repair_messages(
        generated={
            "continue_signal": "后续看有没有更多用户分享类似的数据接入工作流，或者工具开始强调自己的数据连接功能。",
            "title": "AI 做 SEO，光写提示词不够",
        },
        semantic_brief={"plain_chinese_angle": "看真实数据接入是否成为判断标准"},
        issues=["continue_signal: 死物主语做人类动作 `工具开始强调`"],
    )
    prompt = messages[0]["content"] + messages[1]["content"]

    assert "工具开始强调" in prompt
    assert "死物主语" in prompt
    assert "厂商开始宣传" in prompt
    assert "产品页面开始主打" in prompt
    assert "不新增事实" in prompt


def test_v11_report_uses_v10_as_baseline_title_and_route() -> None:
    report = render_v11_markdown_report(
        [
            {
                "lane": "signal",
                "card_id": "signal-1",
                "model": "v10 baseline vs v11 chinese-fluency",
                "baseline": {"title": "V10 标题"},
                "variant": {"title": "V11 标题"},
            }
        ]
    )

    assert "# Hotpost 三 Tab Prompt A/B v11 chinese-fluency 小样本报告" in report
    assert "A baseline: V10 标题" in report
    assert "B variant: V11 标题" in report
    assert "v10 baseline vs v11 chinese-fluency" in report


def test_v11_writes_distinct_artifacts(tmp_path, monkeypatch) -> None:
    from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v11 as v11

    monkeypatch.setattr(v11, "REPORTS_EVALS_DIR", tmp_path)

    json_path, md_path = write_outputs([])

    assert json_path.name == "hotpost_three_tab_prompt_ab_v11_chinese_fluency_results.json"
    assert md_path.name == "hotpost_three_tab_prompt_ab_v11_chinese_fluency_report.md"
    assert json_path.exists()
    assert md_path.exists()


def test_v11_loads_v10_variant_as_baseline(tmp_path) -> None:
    path = tmp_path / "v10.json"
    path.write_text(
        """
[
  {
    "card_id": "card-1",
    "baseline": {"title": "v9 title"},
    "variant": {"title": "v10 title"},
    "semantic_brief": {"plain_chinese_angle": "v10 brief"}
  }
]
""".strip(),
        encoding="utf-8",
    )

    rows = load_v10_baseline_rows(path)

    assert rows["card-1"]["variant"]["title"] == "v10 title"
    assert rows["card-1"]["semantic_brief"]["plain_chinese_angle"] == "v10 brief"
