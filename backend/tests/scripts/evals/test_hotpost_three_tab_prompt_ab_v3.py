from __future__ import annotations

from backend.scripts.evals.run_hotpost_three_tab_prompt_ab_v3 import (
    V3_EXTRA_BANNED_PATTERNS,
    build_v3_semantic_overlay,
    render_v3_markdown_report,
    with_v3_banned_patterns,
)


def test_v3_overlay_carries_semantic_pause_and_depth_rules() -> None:
    overlay = build_v3_semantic_overlay()

    assert "不改 JSON 结构" in overlay
    assert "按语义加标点" in overlay
    assert "逗号、冒号或分号" in overlay
    assert "证据背后的取舍" in overlay
    assert "判断顺序从先" in overlay
    assert "这帖现在值得看" in overlay
    assert "把它们改成具体判断" in overlay
    assert "特别是那些" in overlay
    assert "想用 X 做 Y 的人/团队" in overlay
    assert "尤其是" in overlay
    assert "不输出 `...`" in overlay
    assert "AI 做 SEO，光写提示词不够" in overlay
    assert "判断顺序从" in V3_EXTRA_BANNED_PATTERNS
    assert "这帖现在值得看" in V3_EXTRA_BANNED_PATTERNS


def test_v3_report_uses_v3_title() -> None:
    report = render_v3_markdown_report(
        [
            {
                "lane": "signal",
                "card_id": "signal-1",
                "baseline": {"title": "旧标题"},
                "variant": {"title": "新标题"},
            }
        ]
    )

    assert "# Hotpost 三 Tab Prompt A/B v3 semantic baseline 小样本报告" in report
    assert "旧标题" in report
    assert "新标题" in report


def test_v3_banned_patterns_are_added_without_mutating_rules() -> None:
    rules = {"banned_patterns": {"global": ["existing"]}}

    patched = with_v3_banned_patterns(rules)

    assert "existing" in patched["banned_patterns"]["global"]
    assert "这帖现在值得看" in patched["banned_patterns"]["global"]
    assert "判断顺序从" in patched["banned_patterns"]["global"]
    assert rules["banned_patterns"]["global"] == ["existing"]
