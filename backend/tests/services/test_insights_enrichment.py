from __future__ import annotations

from app.services.analysis.insights_enrichment import (
    build_battlefield_profiles,
    build_top_drivers,
    classify_overall_saturation,
    summarize_trend_series,
)


def test_summarize_trend_series_picks_latest_label() -> None:
    series = [
        {"month": "2024-01", "count": 10, "growth_rate": None, "trend": "➡️ STABLE"},
        {"month": "2024-02", "count": 25, "growth_rate": 1.5, "trend": "📈 RISING"},
    ]

    summary = summarize_trend_series(series, degraded=False, sources=None)

    assert summary["label"] == "持续升温"
    assert "25" in summary["reason"]


def test_classify_overall_saturation_bucket() -> None:
    assert classify_overall_saturation(0.7) == "高饱和"
    assert classify_overall_saturation(0.35) == "中等"
    assert classify_overall_saturation(0.05) == "机会窗口"


def test_build_top_drivers_from_pain_points() -> None:
    pain_points = [
        {"description": "fees are too expensive", "frequency": 20},
        {"description": "pricing is confusing", "frequency": 10},
        {"description": "slow payout and delays", "frequency": 5},
    ]

    drivers = build_top_drivers(pain_points, action_items=None, limit=2)

    assert drivers
    assert drivers[0]["title"] == "透明定价与成本可控"
    assert "fees are too expensive" in drivers[0]["source_pains"][0]


def test_build_battlefield_profiles_uses_pain_counts() -> None:
    communities_detail = [
        {"name": "r/foo", "mentions": 20, "categories": ["tools"]},
        {"name": "r/bar", "mentions": 5, "categories": ["seller"]},
    ]
    pain_counts = {"r/bar": 6, "r/foo": 1}
    pain_points = [
        {
            "description": "fees are too expensive",
            "frequency": 10,
            "example_posts": [
                {"community": "r/bar", "content": "fee issue", "upvotes": 12}
            ],
        }
    ]

    profiles = build_battlefield_profiles(
        communities_detail=communities_detail,
        pain_points=pain_points,
        pain_counts_by_community=pain_counts,
        limit=2,
    )

    assert profiles[0]["communities"] == ["r/bar"]
    assert profiles[0]["evidence_posts"]
