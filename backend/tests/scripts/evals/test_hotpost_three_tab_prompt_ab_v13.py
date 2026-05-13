from __future__ import annotations

from backend.scripts.evals.run_hotpost_three_tab_prompt_ab_v13 import (
    SEMANTIC_MODEL,
    TITLE_ONLY_FIELDS,
    WRITER_MODEL,
    build_title_independence_repair_messages,
    find_v13_title_issues,
    load_v12_baseline_rows,
    merge_title_repair,
    render_v13_markdown_report,
    write_outputs,
)


def test_v13_keeps_approved_combo_model_route() -> None:
    assert SEMANTIC_MODEL == "google/gemini-3-flash-preview"
    assert WRITER_MODEL == "deepseek/deepseek-v4-pro"


def test_v13_is_title_only() -> None:
    assert TITLE_ONLY_FIELDS == {"title"}


def test_v13_detects_title_that_depends_on_summary_line() -> None:
    issues = find_v13_title_issues(
        {
            "title": "写了800行提示词，评论区却在问：这到底是什么？",
            "summary_line": "有用户展示800行提示词工程，但围观者没被行数唬住，反而先质疑定义和实际效果。",
        }
    )

    assert any("这到底是什么" in issue for issue in issues)
    assert any("summary_line" in issue for issue in issues)


def test_v13_detects_title_missing_actor_and_business_context() -> None:
    issues = find_v13_title_issues(
        {
            "title": "移动端转化率卡在2.1%，先看20-30个用户会话回放定位问题",
            "summary_line": "Shopify 卖家移动端 checkout 转化率只有 2.1%，评论建议先看真实会话回放，别再猜按钮颜色。",
            "audience": "正在排查 Shopify 移动端转化问题的电商卖家",
            "why_now": "讨论从猜测页面元素，转到用会话回放看用户到底卡在哪一步。",
        }
    )

    assert any("主体" in issue or "业务场景" in issue for issue in issues)


def test_v13_detects_compact_title_spacing_and_report_words() -> None:
    issues = find_v13_title_issues(
        {
            "title": "评估AI自动化，用户开始先算调教时间和API账单",
            "summary_line": "有用户已经把账摊开：花大量时间调提示词，加上最贵模型的持续账单，可能比自己干还贵。",
        }
    )

    assert any("英文缩写" in issue for issue in issues)

    product_issues = find_v13_title_issues(
        {
            "title": "用Claude Code自动投740份简历，烧掉大量Token只换来12个面试",
            "summary_line": "开发者用 Claude Code 自动投递简历，但 Token 成本很高，面试转化有限。",
        }
    )

    assert any("产品名" in issue or "英文词" in issue for issue in product_issues)

    issues = find_v13_title_issues(
        {
            "title": "800行提示词展示遭评论区质疑定义与实际效用",
            "summary_line": "有用户展示800行提示词工程，但围观者没被行数唬住，反而先质疑定义和实际效果。",
        }
    )

    assert any("书面词" in issue for issue in issues)


def test_v13_detects_clear_but_homepage_unfriendly_long_title() -> None:
    issues = find_v13_title_issues(
        {
            "title": "Shopify 卖家移动端 checkout 转化率卡在 2.1%，先看用户会话回放而不是继续猜按钮颜色",
            "summary_line": "Shopify 卖家移动端 checkout 转化率只有 2.1%，评论建议先看真实会话回放。",
            "audience": "正在排查 Shopify 移动端转化问题的电商卖家",
        }
    )

    assert any("过长" in issue for issue in issues)
    assert any("模板句式" in issue for issue in issues)


def test_v13_detects_community_name_in_title() -> None:
    issues = find_v13_title_issues(
        {
            "title": "r/flashlight 用户拒绝内置电池手电，转向多支可换 21700 电池组合",
            "summary_line": "手电玩家更信任可换电池组合，因为内置电池坏了以后整支手电都失去维护空间。",
        }
    )

    assert any("社区名" in issue for issue in issues)


def test_v13_prompt_requires_standalone_micro_summary_title() -> None:
    messages = build_title_independence_repair_messages(
        generated={
            "title": "写了800行提示词，评论区却在问：这到底是什么？",
            "summary_line": "有用户展示800行提示词工程，但围观者没被行数唬住，反而先质疑定义和实际效果。",
            "why_now": "围观者开始追问定义和价值。",
        },
        semantic_brief={"plain_chinese_angle": "行数不能证明提示词工程有价值"},
        issues=["title: 依赖 summary_line 才能看懂"],
    )
    prompt = messages[0]["content"] + messages[1]["content"]

    assert "只输出 JSON" in prompt
    assert "只允许输出 title" in prompt
    assert "不看 summary_line" in prompt
    assert "首页可扫读标题" in prompt
    assert "原有对象、变化/冲突和核心意思不能丢" in prompt
    assert "谁，在什么对象上，出现了什么明确变化" in prompt
    assert "Shopify 卖家" in prompt
    assert "不要统一套模板" in prompt
    assert "社区名默认不进标题" in prompt
    assert "实际效用" in prompt
    assert "AI 自动化" in prompt
    assert "18-32" in prompt
    assert "google/gemini-3-flash-preview" in prompt
    assert "deepseek/deepseek-v4-pro" in prompt


def test_v13_merge_only_changes_title() -> None:
    original = {
        "title": "旧标题",
        "summary_line": "摘要不能动",
        "why_now": "why_now 不能动",
    }

    merged = merge_title_repair(original, {"title": "新标题", "summary_line": "不该改"})

    assert merged["title"] == "新标题"
    assert merged["summary_line"] == "摘要不能动"
    assert merged["why_now"] == "why_now 不能动"


def test_v13_report_is_title_focused() -> None:
    report = render_v13_markdown_report(
        [
            {
                "lane": "breakdown",
                "card_id": "card-1",
                "model": "v12 baseline vs v13 title-standalone",
                "baseline": {"title": "V12 标题", "summary_line": "摘要"},
                "variant": {"title": "V13 标题", "summary_line": "摘要"},
                "v13_title_issues_before": ["title: issue"],
                "v13_title_issues_after": [],
            }
        ]
    )

    assert "# Hotpost 三 Tab Prompt A/B v13 title-standalone 小样本报告" in report
    assert "A title: V12 标题" in report
    assert "B title: V13 标题" in report
    assert "summary_line: 摘要" in report
    assert "v12 baseline vs v13 title-standalone" in report


def test_v13_writes_distinct_artifacts(tmp_path, monkeypatch) -> None:
    from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v13 as v13

    monkeypatch.setattr(v13, "REPORTS_EVALS_DIR", tmp_path)

    json_path, md_path = write_outputs([])

    assert json_path.name == "hotpost_three_tab_prompt_ab_v13_title_standalone_results.json"
    assert md_path.name == "hotpost_three_tab_prompt_ab_v13_title_standalone_report.md"
    assert json_path.exists()
    assert md_path.exists()


def test_v13_loads_v12_variant_as_baseline(tmp_path) -> None:
    path = tmp_path / "v12.json"
    path.write_text(
        """
[
  {
    "card_id": "card-1",
    "baseline": {"title": "v11 title"},
    "variant": {"title": "v12 title"},
    "semantic_brief": {"plain_chinese_angle": "v12 brief"}
  }
]
""".strip(),
        encoding="utf-8",
    )

    rows = load_v12_baseline_rows(path)

    assert rows["card-1"]["variant"]["title"] == "v12 title"
    assert rows["card-1"]["semantic_brief"]["plain_chinese_angle"] == "v12 brief"
