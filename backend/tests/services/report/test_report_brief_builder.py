from __future__ import annotations

import json

from app.services.report.report_brief_builder import build_narrative_report_brief


def test_build_narrative_report_brief_keeps_structure_and_evidence_titles() -> None:
    brief = build_narrative_report_brief(
        report_structured={
            "decision_cards": [
                {"title": "需求趋势", "conclusion": "热度稳定", "details": ["样本稳定"]}
            ],
            "battlefields": [
                {
                    "name": "r/startups",
                    "subreddits": ["r/startups"],
                    "profile": "创业团队",
                    "strategy_advice": "先看增长",
                }
            ],
            "pain_points": [
                {
                    "title": "支付页面太复杂",
                    "user_voices": ["结账太慢了"],
                    "interpretation": "流程过长影响转化",
                    "evidence_chain": [
                        {
                            "title": "真实反馈",
                            "url": "https://www.reddit.com/r/startups/comments/demo",
                            "note": "r/startups",
                        }
                    ],
                }
            ],
            "drivers": [{"title": "更快完成上手", "description": "节省时间"}],
            "opportunities": [
                {
                    "title": "引导式新手上手包",
                    "target_communities": ["r/startups"],
                    "evidence_chain": [
                        {
                            "title": "真实反馈",
                            "url": "https://www.reddit.com/r/startups/comments/demo",
                            "note": "r/startups",
                        }
                    ],
                }
            ],
        },
        facts_slice={
            "trend_summary": {"summary": "讨论热度稳定"},
            "market_saturation": {"summary": "竞争中等"},
            "sample_comments_db": [{"body": "too noisy"}],
        },
    )

    payload = json.loads(brief)
    assert payload["section_contract"][0] == "1. 开篇概览"
    assert payload["canonical_titles"]["pain_points"] == ["支付页面太复杂"]
    assert payload["canonical_titles"]["opportunities"] == ["引导式新手上手包"]
    assert payload["evidence_contract"]["pain_points"][0]["evidence_chain"][0]["url"] == (
        "https://www.reddit.com/r/startups/comments/demo"
    )
    assert "sample_comments_db" not in payload["facts_focus"]
