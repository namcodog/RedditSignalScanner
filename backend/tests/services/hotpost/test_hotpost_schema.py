from __future__ import annotations

import pytest

from app.schemas.hotpost import HotpostDebugInfo, HotpostSearchRequest, HotpostSearchResponse


def test_subreddits_limit_allows_10() -> None:
    subreddits = [f"r/test{i}" for i in range(10)]
    req = HotpostSearchRequest(query="test", subreddits=subreddits)
    assert req.subreddits is not None
    assert len(req.subreddits) == 10


def test_subreddits_limit_rejects_11() -> None:
    subreddits = [f"r/test{i}" for i in range(11)]
    with pytest.raises(ValueError):
        HotpostSearchRequest(query="test", subreddits=subreddits)


def test_hotpost_response_debug_info_is_typed() -> None:
    response = HotpostSearchResponse(
        query_id="test-id",
        query="robot vacuum",
        mode="trending",
        search_time="2026-03-15T00:00:00+00:00",
        from_cache=False,
        summary="summary",
        top_posts=[],
        key_comments=[],
        communities=[],
        related_queries=[],
        evidence_count=0,
        community_distribution={},
        sentiment_overview={"positive": 0.0, "neutral": 0.0, "negative": 0.0},
        confidence="none",
        debug_info={
            "query_source": "llm",
            "summary_source": "fallback",
            "report_source": "disabled",
            "degraded_reasons": ["llm_generate_failed"],
        },
    )

    assert isinstance(response.debug_info, HotpostDebugInfo)
    assert response.debug_info is not None
    assert response.debug_info.query_source == "llm"
    assert response.debug_info.summary_source == "fallback"
    assert response.debug_info.report_source == "disabled"
    assert response.debug_info.degraded_reasons == ["llm_generate_failed"]
