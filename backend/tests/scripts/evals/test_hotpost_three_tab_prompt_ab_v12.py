from __future__ import annotations

from backend.scripts.evals.run_hotpost_three_tab_prompt_ab_v12 import (
    CONCISE_TARGET_FIELDS,
    WRITER_MODEL,
    build_high_density_repair_messages,
    find_v12_density_issues,
    load_v11_baseline_rows,
    render_v12_markdown_report,
    write_outputs,
)


def test_v12_keeps_mimo_writer_for_high_density_repair() -> None:
    assert WRITER_MODEL == "xiaomi/mimo-v2.5-pro"


def test_v12_only_targets_user_visible_reading_load_fields() -> None:
    assert CONCISE_TARGET_FIELDS == {
        "title",
        "summary_line",
        "why_now",
        "why_test_now",
        "continue_signal",
        "stop_signal",
        "flashpoint",
        "fight_line",
    }


def test_v12_detects_verbose_low_density_copy_in_target_fields_only() -> None:
    issues = find_v12_density_issues(
        {
            "why_now": "有用户把 Claude 连上了自己的网站代码库和搜索数据工具，拿到了更落地的建议。社区反应是：很多 AI SEO 工具只是‘打磨过的猜测’，能接入真实数据才是关键。所以，下一步选工具或优化流程，应该先看它能不能连上你的代码和数据，而不是先研究提示词技巧。",
            "audience": "想用 AI 做 SEO 的人，这个字段即使稍长也不是本轮重点。",
            "title": "AI 做 SEO，光写提示词不够；还得看网站代码和搜索数据",
        }
    )

    assert any("why_now" in issue for issue in issues)
    assert not any("audience" in issue for issue in issues)


def test_v12_detects_clickbait_compression_words() -> None:
    issues = find_v12_density_issues(
        {
            "title": "全自动AI代理梦碎：开发者承认，能上线的只有智能助手",
        }
    )

    assert any("梦碎" in issue for issue in issues)


def test_v12_does_not_fail_clear_copy_only_because_it_is_long() -> None:
    issues = find_v12_density_issues(
        {
            "why_now": "Shopify 卖家把移动端 checkout 转化率拆开看后，发现加购率没有明显掉，但支付页退出很多，判断重点转到结账交互细节和真实会话回放。",
            "title": "Shopify 卖家移动端 checkout 转化率卡在 2.1%，先看用户会话回放",
        }
    )

    assert issues == []


def test_v12_does_not_fail_business_context_words_without_action_advice() -> None:
    issues = find_v12_density_issues(
        {
            "title": "电商卖家选工具，先问是不是同一套系统，不再先问能不能集成",
            "why_now": "卖家把结账工具和订阅工具分开看，因为转化率和留存率的优先级天然不同。",
        }
    )

    assert issues == []


def test_v12_repair_prompt_preserves_information_density_not_hard_compression() -> None:
    messages = build_high_density_repair_messages(
        generated={
            "summary_line": "有用户已经把判断标准从‘提示词写得好不好’，转成‘工具能不能接入真实代码和数据’。评论里直接说，这才是关键。",
            "why_now": "有用户把 Claude 连上了自己的网站代码库和搜索数据工具，拿到了更落地的建议。社区反应是：很多 AI SEO 工具只是‘打磨过的猜测’，能接入真实数据才是关键。所以，下一步选工具或优化流程，应该先看它能不能连上你的代码和数据，而不是先研究提示词技巧。",
            "audience": "想用 AI 做 SEO 的人",
        },
        semantic_brief={"plain_chinese_angle": "判断重点从提示词转到真实数据接入"},
        issues=["why_now: 重点字段过长，阅读负担高"],
    )
    prompt = messages[0]["content"] + messages[1]["content"]

    assert "不是压缩信息" in prompt
    assert "信息密度" in prompt
    assert "不删关键证据" in prompt
    assert "只改 target_fields" in prompt
    assert "title" in prompt
    assert "why_now" in prompt
    assert "梦碎" in prompt
    assert "标题党" in prompt
    assert "why_now 只回答" in prompt
    assert "不要顺手给行动建议" in prompt


def test_v12_report_uses_v11_as_baseline_title_and_route() -> None:
    report = render_v12_markdown_report(
        [
            {
                "lane": "signal",
                "card_id": "signal-1",
                "model": "v11 baseline vs v12 high-density-concise",
                "baseline": {"title": "V11 标题"},
                "variant": {"title": "V12 标题"},
            }
        ]
    )

    assert "# Hotpost 三 Tab Prompt A/B v12 high-density-concise 小样本报告" in report
    assert "A baseline: V11 标题" in report
    assert "B variant: V12 标题" in report
    assert "v11 baseline vs v12 high-density-concise" in report


def test_v12_writes_distinct_artifacts(tmp_path, monkeypatch) -> None:
    from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v12 as v12

    monkeypatch.setattr(v12, "REPORTS_EVALS_DIR", tmp_path)

    json_path, md_path = write_outputs([])

    assert json_path.name == "hotpost_three_tab_prompt_ab_v12_high_density_concise_results.json"
    assert md_path.name == "hotpost_three_tab_prompt_ab_v12_high_density_concise_report.md"
    assert json_path.exists()
    assert md_path.exists()


def test_v12_loads_v11_variant_as_baseline(tmp_path) -> None:
    path = tmp_path / "v11.json"
    path.write_text(
        """
[
  {
    "card_id": "card-1",
    "baseline": {"title": "v10 title"},
    "variant": {"title": "v11 title"},
    "semantic_brief": {"plain_chinese_angle": "v11 brief"}
  }
]
""".strip(),
        encoding="utf-8",
    )

    rows = load_v11_baseline_rows(path)

    assert rows["card-1"]["variant"]["title"] == "v11 title"
    assert rows["card-1"]["semantic_brief"]["plain_chinese_angle"] == "v11 brief"
