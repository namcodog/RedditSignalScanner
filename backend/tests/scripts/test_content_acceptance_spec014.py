from __future__ import annotations

from scripts.content_acceptance import _check_quality


def _base_report() -> dict:
    return {
        "task_id": "dummy-task",
        "stats": {
            "positive_mentions": 1,
            "negative_mentions": 1,
            "neutral_mentions": 0,
            "total_mentions": 2,
        },
        "overview": {
            "top_communities": [
                {"name": "r/A", "category": "x", "mentions": 3},
                {"name": "r/B", "category": "x", "mentions": 2},
                {"name": "r/C", "category": "x", "mentions": 1},
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
                {"description": "p1", "frequency": 1, "sentiment_score": -0.2, "example_posts": []}
            ],
            "entity_summary": {"brands": [{"name": "X", "mentions": 1}]},
            "pain_clusters": [
                {"topic": "t1", "negative_mean": -0.3, "communities_count": 1, "top_communities": [], "samples": ["s1"]},
                {"topic": "t2", "negative_mean": -0.2, "communities_count": 1, "top_communities": [], "samples": ["s2"]},
            ],
            "competitor_layers_summary": [
                {"layer": "workspace", "label": "Workspace", "top_competitors": [], "threats": ""},
                {"layer": "analytics", "label": "Analytics", "top_competitors": [], "threats": ""},
            ],
            "opportunities": [
                {
                    "description": "Opportunity A",
                    "relevance_score": 0.7,
                    "potential_users": "约10个潜在团队",
                    "potential_users_est": 10,
                    "key_insights": ["k1"],
                    "source_examples": [],
                }
            ],
        },
    }


def test_battle_recommendations_field_present_and_true_when_ge_3():
    report = _base_report()
    result = _check_quality(report)
    assert result.get("battle_recommendations_ok") is True
    # passed should not depend on this optional gate by default
    assert result.get("passed") is True


def test_battle_recommendations_field_false_when_lt_3():
    report = _base_report()
    report["overview"]["top_communities"] = report["overview"]["top_communities"][:2]
    result = _check_quality(report)
    assert result.get("battle_recommendations_ok") is False
    # still not enforced by default
    assert result.get("passed") is True

