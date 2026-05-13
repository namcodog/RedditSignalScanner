from __future__ import annotations

from backend.scripts.evals.run_hotpost_three_tab_prompt_ab_v2 import (
    build_v2_baseline_overlay,
    render_v2_markdown_report,
)


def test_v2_overlay_carries_user_approved_boundaries() -> None:
    overlay = build_v2_baseline_overlay()

    assert "不新增字段" in overlay
    assert "不改 JSON 结构" in overlay
    assert "不套固定结构" in overlay
    assert "这帖火了" in overlay
    assert "AI 做 SEO，光写提示词不够" in overlay
    assert "模型跑分高不一定好用" in overlay


def test_v2_report_uses_v2_title() -> None:
    report = render_v2_markdown_report(
        [
            {
                "lane": "signal",
                "card_id": "signal-1",
                "baseline": {"title": "旧标题"},
                "variant": {"title": "新标题"},
            }
        ]
    )

    assert "# Hotpost 三 Tab Prompt A/B v2 baseline 小样本报告" in report
    assert "旧标题" in report
    assert "新标题" in report
