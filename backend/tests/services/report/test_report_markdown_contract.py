from __future__ import annotations

from app.services.report.report_markdown_contract import (
    validate_narrative_markdown_against_canonical,
)


def _build_structured() -> dict[str, object]:
    return {
        "decision_cards": [
            {"title": "需求趋势", "conclusion": "热度稳定", "details": ["样本稳定"]}
        ],
        "market_health": {
            "competition_saturation": {
                "level": "中等",
                "details": ["已有讨论"],
                "interpretation": "仍有空间",
            },
            "ps_ratio": {
                "ratio": "1.2:1",
                "conclusion": "问题略多",
                "interpretation": "可继续深挖",
                "health_assessment": "可做",
            },
        },
        "battlefields": [{"name": "r/startups"}],
        "pain_points": [{"title": "支付页面太复杂"}],
        "drivers": [{"title": "更快完成上手"}],
        "opportunities": [{"title": "引导式新手上手包"}],
    }


def test_validate_narrative_markdown_against_canonical_accepts_aligned_markdown() -> None:
    markdown = """# Demo report

## 1. 开篇概览
内容

## 2. 决策风向标
需求趋势

## 3. 概览（市场健康度诊断）
内容

## 4. 核心战场推荐（画像分级）
r/startups

## 5. 用户痛点拆解
支付页面太复杂

## 6. 关键决策驱动力
更快完成上手

## 7. 商业机会
引导式新手上手包
"""
    assert (
        validate_narrative_markdown_against_canonical(
            markdown=markdown,
            report_structured=_build_structured(),
        )
        == []
    )


def test_validate_narrative_markdown_against_canonical_rejects_missing_titles() -> None:
    markdown = """# Demo report

## 1. 开篇概览
内容

## 2. 决策风向标
需求趋势

## 7. 商业机会
别的机会
"""
    issues = validate_narrative_markdown_against_canonical(
        markdown=markdown,
        report_structured=_build_structured(),
    )
    assert "missing markdown section 4" in issues
    assert "opportunity missing from markdown section 7: 引导式新手上手包" in issues
