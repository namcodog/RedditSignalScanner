from __future__ import annotations

import pytest

from app.services.analysis import sample_guard
from app.services.analysis.sample_guard import SampleCheckResult


@pytest.mark.asyncio
async def test_check_sample_size_returns_without_supplement(monkeypatch: pytest.MonkeyPatch) -> None:
    """When hot+cold samples meet the floor, no supplement should trigger."""

    hot_posts = [{"id": f"h{i}", "source_type": "cache"} for i in range(900)]
    cold_posts = [{"id": f"c{i}", "source_type": "cold"} for i in range(700)]
    supplement_called: dict[str, bool] = {"value": False}

    async def fake_hot_fetcher(**_: object) -> list[dict]:
        return hot_posts

    async def fake_cold_fetcher(**_: object) -> list[dict]:
        return cold_posts

    async def fake_supplementer(**_: object) -> list[dict]:
        supplement_called["value"] = True
        return []

    result = await sample_guard.check_sample_size(
        hot_fetcher=fake_hot_fetcher,
        cold_fetcher=fake_cold_fetcher,
        supplementer=fake_supplementer,
        keywords=["automation", "research"],
        min_samples=1500,
        lookback_days=30,
    )

    assert isinstance(result, SampleCheckResult)
    assert result.hot_count == len(hot_posts)
    assert result.cold_count == len(cold_posts)
    assert result.combined_count == len(hot_posts) + len(cold_posts)
    assert result.shortfall == 0
    assert result.supplemented is False
    assert supplement_called["value"] is False
    assert result.supplement_posts == []


@pytest.mark.asyncio
async def test_check_sample_size_triggers_supplement_when_shortfall(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shortfall should invoke keyword crawl supplementer and annotate posts."""

    hot_posts = [{"id": f"h{i}", "source_type": "cache"} for i in range(200)]
    cold_posts = [{"id": f"c{i}", "source_type": "cold"} for i in range(300)]
    requested: dict[str, object] = {}

    async def fake_hot_fetcher(**kwargs: object) -> list[dict]:
        requested["hot_kwargs"] = kwargs
        return hot_posts

    async def fake_cold_fetcher(**kwargs: object) -> list[dict]:
        requested["cold_kwargs"] = kwargs
        return cold_posts

    async def fake_supplementer(**kwargs: object) -> list[dict]:
        requested["supp_kwargs"] = kwargs
        return [
            {
                "id": "search-1",
                "title": "Looking for a better automation workflow",
                "summary": "Need urgent automation tooling that can scale.",
                "score": 88,
                "num_comments": 11,
                "subreddit": "r/startups",
                "source_type": "search",
            },
            {
                "id": "search-2",
                "title": "Would pay for AI summaries",
                "summary": "Willing to pay for AI summaries that save four hours weekly.",
                "score": 64,
                "num_comments": 9,
                "subreddit": "r/artificial",
                "source_type": "search",
            },
        ]

    result = await sample_guard.check_sample_size(
        hot_fetcher=fake_hot_fetcher,
        cold_fetcher=fake_cold_fetcher,
        supplementer=fake_supplementer,
        keywords=["automation", "ai", "summary"],
        min_samples=1500,
        lookback_days=30,
    )

    assert result.supplemented is True
    assert result.hot_count == len(hot_posts)
    assert result.cold_count == len(cold_posts)
    assert result.shortfall == 1500 - (len(hot_posts) + len(cold_posts))
    assert len(result.supplement_posts) == 2
    assert all(post["source_type"] == "search" for post in result.supplement_posts)
    # Ensure fetchers received context parameters (lookback, keywords)
    assert "lookback_days" in requested.get("hot_kwargs", {})
    assert "keywords" in requested.get("supp_kwargs", {})
