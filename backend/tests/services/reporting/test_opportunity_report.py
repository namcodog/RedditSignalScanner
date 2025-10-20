from __future__ import annotations

from app.services.reporting.opportunity_report import build_opportunity_reports


def _build_insights() -> dict[str, object]:
    return {
        "pain_points": [
            {
                "description": "Onboarding流程复杂",
                "frequency": 12,
                "sentiment_score": -0.4,
                "severity": "high",
                "example_posts": [
                    {
                        "community": "r/startups",
                        "content": "我们的SaaS注册环节太复杂了",
                        "url": "https://reddit.com/r/startups/1",
                        "upvotes": 42,
                    }
                ],
                "user_examples": [
                    "用户抱怨整个流程要花30分钟",
                    "新手完全不知道下一步怎么走",
                ],
            }
        ],
        "opportunities": [
            {
                "description": "自动化Onboarding机器人",
                "relevance_score": 0.72,
                "potential_users": "约450个潜在团队",
                "key_insights": ["机器人引导能降低流失", "需要支持多语言"],
                "source_examples": [
                    {
                        "community": "r/saas",
                        "content": "有没有自动 onboarding 的工具？",
                        "url": "https://reddit.com/r/saas/2",
                        "upvotes": 28,
                    }
                ],
            }
        ],
        "competitors": [],
    }


def test_build_opportunity_reports_generates_priority() -> None:
    insights = _build_insights()
    reports = build_opportunity_reports(insights)
    assert len(reports) == 1
    report = reports[0]
    assert report.problem_definition.startswith("自动化Onboarding")
    assert report.priority > 0
    assert report.confidence > 0.7
    assert report.urgency >= 0.9
    assert report.evidence_chain
    assert report.suggested_actions

