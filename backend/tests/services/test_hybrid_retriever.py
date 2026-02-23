import pytest

from app.services.analysis.hybrid_retriever import fetch_hybrid_posts


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
