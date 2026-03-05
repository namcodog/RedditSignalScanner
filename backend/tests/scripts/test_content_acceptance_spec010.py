from __future__ import annotations

import pytest
import importlib

try:
    from scripts.content_acceptance import _check_quality
except (ImportError, ModuleNotFoundError) as exc:
    pytest.skip(str(exc), allow_module_level=True)


def _base_report() -> dict:
    return {
        "task_id": "dummy-task",
        "stats": {
            "positive_mentions": 10,
            "negative_mentions": 5,
            "neutral_mentions": 5,
            "total_mentions": 20,
        },
        "overview": {
            "top_communities": [
                {"name": "r/startups", "category": "business", "mentions": 5}
            ]
        },
        "report": {
            "action_items": [
                {
                    "problem_definition": "Do X",
                    "evidence_chain": [
                        {"title": "e1", "url": "https://example.com/1", "note": "n1"},
                        {"title": "e2", "url": "https://example.com/2", "note": "n2"},
                    ],
                }
            ],
            "pain_points": [
                {"description": "p1", "frequency": 2, "sentiment_score": -0.3, "example_posts": []},
                {"description": "p2", "frequency": 1, "sentiment_score": -0.4, "example_posts": []},
                {"description": "p3", "frequency": 1, "sentiment_score": -0.2, "example_posts": []},
            ],
            # entity_summary 需要>=3条用于通过现有关卡
            "entity_summary": {
                "brands": [{"name": "Notion", "mentions": 3}],
                "features": [{"name": "automation", "mentions": 2}],
                "pain_points": [{"name": "slow", "mentions": 2}],
            },
            # 以下三项为 Spec010 新增硬门禁所需
            "pain_clusters": [
                {"topic": "t1", "negative_mean": -0.3, "communities_count": 1, "top_communities": [], "samples": []},
                {"topic": "t2", "negative_mean": -0.2, "communities_count": 1, "top_communities": [], "samples": []},
            ],
            "competitor_layers_summary": [
                {"layer": "workspace", "label": "Workspace", "top_competitors": [], "threats": ""},
                {"layer": "analytics", "label": "Analytics", "top_competitors": [], "threats": ""},
            ],
            "opportunities": [
                {
                    "description": "Opportunity A",
                    "relevance_score": 0.7,
                    "potential_users": "约120个潜在团队",
                    "potential_users_est": 120,
                    "key_insights": ["k1", "k2"],
                    "source_examples": [],
                }
            ],
        },
    }


def test_spec010_hard_gates_fail_when_missing():
    report = _base_report()
    # 删除 clusters 以触发失败
    report["report"]["pain_clusters"] = []
    result = _check_quality(report)
    assert result.get("clusters_ok") is False
    assert result.get("passed") is False

    # 缺少 competitor_layers_summary 触发失败
    report = _base_report()
    report["report"]["competitor_layers_summary"] = []
    result = _check_quality(report)
    assert result.get("competitor_layers_ok") is False
    assert result.get("passed") is False

    # 缺少数值型 potential_users_est 或 <=0 触发失败
    report = _base_report()
    report["report"]["opportunities"][0].pop("potential_users_est", None)
    result = _check_quality(report)
    assert result.get("opportunity_users_ok") is False
    assert result.get("passed") is False

    report = _base_report()
    report["report"]["opportunities"][0]["potential_users_est"] = 0
    result = _check_quality(report)
    assert result.get("opportunity_users_ok") is False
    assert result.get("passed") is False


def test_spec010_hard_gates_pass_when_valid():
    report = _base_report()
    result = _check_quality(report)
    assert result.get("clusters_ok") is True
    assert result.get("competitor_layers_ok") is True
    assert result.get("opportunity_users_ok") is True
    assert result.get("passed") is True
