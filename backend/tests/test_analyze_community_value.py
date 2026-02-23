import pandas as pd
import pytest

from backend.scripts.analyze_community_value import compute_rfe_profile


def test_compute_rfe_profile_assigns_archetypes_and_scores() -> None:
    stats = pd.DataFrame(
        [
            {
                "subreddit": "r/hightraffic",
                "total_posts": 600,
                "total_interactions": 0,
                "avg_engagement": 10.0,
                "max_engagement": 80,
            },
            {
                "subreddit": "r/hiddengem",
                "total_posts": 120,
                "total_interactions": 0,
                "avg_engagement": 55.0,
                "max_engagement": 300,
            },
            {
                "subreddit": "r/solidgold",
                "total_posts": 180,
                "total_interactions": 0,
                "avg_engagement": 25.0,
                "max_engagement": 150,
            },
            {
                "subreddit": "r/growing",
                "total_posts": 30,
                "total_interactions": 0,
                "avg_engagement": 5.0,
                "max_engagement": 25,
            },
        ]
    )

    profile = compute_rfe_profile(stats).set_index("Subreddit")

    assert profile.loc["r/hightraffic", "Archetype"] == "🔥 High Traffic"
    assert profile.loc["r/hightraffic", "F"] == pytest.approx(6.7)
    assert profile.loc["r/hightraffic", "Score"] == pytest.approx(27.8)

    assert profile.loc["r/hiddengem", "Archetype"] == "💎 Hidden Gem"
    assert profile.loc["r/hiddengem", "F"] == pytest.approx(1.3)
    assert profile.loc["r/hiddengem", "Score"] == pytest.approx(114.6)

    assert profile.loc["r/solidgold", "Archetype"] == "⭐ Solid Gold"
    assert profile.loc["r/solidgold", "E"] == pytest.approx(25.0)

    assert profile.loc["r/growing", "Archetype"] == "🌱 Growing"
    assert profile.loc["r/growing", "Score"] == pytest.approx(7.5)
