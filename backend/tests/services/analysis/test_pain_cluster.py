import math

import pytest

from app.services.analysis.pain_cluster import cluster_pain_points


def _pain_point(
    description: str,
    *,
    sentiment: float = -0.6,
    frequency: int = 20,
    community: str = "r/test",
    user_examples: list[str] | None = None,
) -> dict:
    return {
        "description": description,
        "frequency": frequency,
        "sentiment_score": sentiment,
        "severity": "high" if sentiment <= -0.4 else "medium",
        "example_posts": [
            {
                "community": community,
                "content": description,
                "url": f"https://reddit.com/{community}/{abs(hash(description)) % 1000}",
            }
        ],
        "user_examples": user_examples or [f"{description} -- user quote"],
    }


def test_cluster_groups_similar_descriptions() -> None:
    pains = [
        _pain_point("Onboarding workflow is painfully slow for new sellers"),
        _pain_point(
            "New seller onboarding is slow and confusing across teams",
            frequency=25,
            community="r/crossbordertrade",
        ),
        _pain_point(
            "Logistics fees are skyrocketing after the latest policy",
            sentiment=-0.4,
            community="r/logistics",
        ),
        _pain_point(
            "Paid ads on TikTok feel wasteful without better attribution",
            sentiment=-0.35,
            community="r/marketing",
        ),
    ]

    clusters = cluster_pain_points(pains, min_clusters=3, max_clusters=5)

    assert 3 <= len(clusters) <= 5

    topics = {cluster["topic"].lower() for cluster in clusters}
    assert any("onboard" in topic for topic in topics)

    onboarding_cluster = next(
        cluster for cluster in clusters if "onboard" in cluster["topic"].lower()
    )
    assert onboarding_cluster["communities_count"] >= 1
    assert math.isclose(onboarding_cluster["negative_mean"], -0.6, abs_tol=0.2)
    assert len(onboarding_cluster["samples"]) >= 2


def test_cluster_handles_small_input() -> None:
    single = [
        _pain_point(
            "Returns process is confusing for EU orders",
            sentiment=-0.55,
            community="r/ecommercetips",
        )
    ]

    clusters = cluster_pain_points(single)
    assert len(clusters) == 1
    assert clusters[0]["topic"]
    assert clusters[0]["communities_count"] == 1
    assert clusters[0]["samples"][0].startswith("Returns process")


def test_cluster_topic_fallback_to_description() -> None:
    pains = [
        _pain_point("aaa aaa aaa", sentiment=-0.2),
        _pain_point("bbb bbb", sentiment=-0.2),
    ]

    clusters = cluster_pain_points(pains, min_clusters=1, max_clusters=2)
    assert len(clusters) >= 1
    assert all(cluster["topic"] for cluster in clusters)
