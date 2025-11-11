from __future__ import annotations

from backend.app.services.reporting.opportunity_report import build_opportunity_reports


def test_build_opportunity_reports_uses_numeric_est_for_product_fit() -> None:
    insights = {
        "pain_points": [
            {
                "description": "Export is unreliable",
                "frequency": 4,
                "sentiment_score": -0.6,
                "severity": "high",
                "example_posts": [
                    {"community": "r/test", "content": "Export failed again"}
                ],
            }
        ],
        "opportunities": [
            {
                "description": "Need automated exports",
                "relevance_score": 0.8,
                "potential_users": "约120个潜在团队",
                "potential_users_est": 600,
                "key_insights": ["automation", "schedule"],
                "source_examples": [
                    {"community": "r/test", "content": "I want scheduled export"}
                ],
            }
        ],
    }

    reports = build_opportunity_reports(insights)
    assert reports, "expected at least one report"
    top = reports[0]
    # 数值估计600 → product_fit 应为0.9
    assert abs(top.product_fit - 0.9) < 1e-6
    # priority 合理区间（>0）
    assert top.priority > 0.0

