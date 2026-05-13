from __future__ import annotations

from dataclasses import dataclass

from app.services.report.structured_report_renderer import (
    render_structured_report_markdown,
)


@dataclass
class _PainPointStub:
    example_posts: list[dict[str, str]]


def test_render_structured_report_markdown_returns_none_for_empty_payload() -> None:
    assert (
        render_structured_report_markdown(
            None,
            product_description="Demo",
            facts_slice=None,
            pain_points=None,
        )
        is None
    )


def test_render_structured_report_markdown_renders_key_sections() -> None:
    markdown = render_structured_report_markdown(
        {
            "decision_cards": [
                {
                    "title": "需求趋势",
                    "conclusion": "刚需明确",
                    "details": ["复购强", "讨论持续上升"],
                },
                {
                    "title": "核心社群",
                    "conclusion": "核心人群集中在 r/espresso",
                },
            ],
            "market_health": {
                "competition_saturation": {
                    "level": "中等",
                    "details": ["同类产品不少"],
                    "interpretation": "还能切细分位",
                },
                "ps_ratio": {
                    "ratio": "1.2:1",
                    "conclusion": "问题略多于攻略",
                    "interpretation": "还有优化空间",
                },
            },
            "battlefields": [
                {
                    "name": "咖啡爱好者",
                    "subreddits": ["r/espresso", "r/coffee"],
                    "profile": "重度用户",
                    "pain_points": ["清洁麻烦", "配件贵"],
                    "strategy_advice": "先打耗材和清洁方案",
                }
            ],
            "pain_points": [
                {
                    "title": "维护成本高",
                    "user_voices": ["清洁太麻烦了"],
                    "data_impression": "高频抱怨",
                    "interpretation": "售后与耗材有机会",
                }
            ],
            "drivers": [
                {"title": "口味提升", "description": "愿意为稳定风味买单"},
            ],
            "opportunities": [
                {
                    "title": "清洁套装",
                    "target_pain_points": ["维护成本高"],
                    "target_communities": ["r/espresso"],
                    "product_positioning": "新手友好",
                    "core_selling_points": ["一步清洁", "配件齐全"],
                }
            ],
        },
        product_description="意式咖啡清洁套装",
        facts_slice={
            "aggregates": {
                "communities": [
                    {"name": "r/espresso", "posts": 12, "comments": 48},
                    {"name": "r/coffee", "posts": 8, "comments": 20},
                ]
            }
        },
        pain_points=[
            _PainPointStub(
                example_posts=[
                    {
                        "url": "https://reddit.com/post-1",
                        "title": "Cleaning routine takes forever",
                    }
                ]
            )
        ],
    )

    assert markdown is not None
    assert "# 市场洞察报告" in markdown
    assert "- 标题：意式咖啡清洁套装 · 市场洞察报告" in markdown
    assert "- 核心社区：r/espresso, r/coffee" in markdown
    assert "- 数据量级：约 20 帖 / 68 评论" in markdown
    assert "### 战场 1：咖啡爱好者" in markdown
    assert "### 1. 维护成本高" in markdown
    assert "[Cleaning routine takes forever](https://reddit.com/post-1)" in markdown
    assert "### 机会卡 1：清洁套装" in markdown
