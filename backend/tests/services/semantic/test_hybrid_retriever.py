import pytest

from app.services.analysis.hybrid_retriever import (
    _build_search_query,
    fetch_hybrid_posts,
    run_hybrid_retrieval,
)


@pytest.mark.asyncio
async def test_fetch_hybrid_posts_empty_tokens_returns_empty() -> None:
    class DummySession:
        pass

    result = await fetch_hybrid_posts(
        DummySession(),
        topic="test",
        topic_tokens=[],
        days=30,
    )

    assert result == []


def test_build_search_query_sanitizes_and_dedupes_tokens() -> None:
    query = _build_search_query(["Shopify Ads", "shopify ads", "cpc!!!", "\"bad\" token"])

    assert query == "\"shopify ads\" OR cpc OR \"bad token\""


@pytest.mark.asyncio
async def test_run_hybrid_retrieval_skips_when_tokens_are_not_searchable() -> None:
    class DummySession:
        pass

    result = await run_hybrid_retrieval(
        DummySession(),
        topic="test",
        topic_tokens=["!!!", "   "],
        days=30,
    )

    assert result.status == "skipped"
    assert result.reason == "no_search_terms"
    assert result.posts == []
