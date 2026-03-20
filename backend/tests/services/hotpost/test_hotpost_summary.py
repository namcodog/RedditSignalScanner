from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.schemas.hotpost import Hotpost
from app.services.hotpost.service import HotpostService
from app.core.config import Settings
from app.services.hotpost.result_meta import HotpostLLMReportResult, HotpostSummaryResult


def test_fallback_summary_includes_signals_and_sentiment() -> None:
    post = Hotpost(
        rank=1,
        id="p1",
        title="Too expensive and confusing",
        body_preview="body",
        score=10,
        num_comments=2,
        heat_score=14,
        rant_score=12.0,
        rant_signals=["expensive"],
        subreddit="r/test",
        author="user",
        reddit_url="https://www.reddit.com/r/test/comments/p1",
        created_utc=0.0,
        signals=["expensive", "confusing"],
        signal_score=12.0,
        top_comments=[],
    )
    summary = HotpostService._fallback_summary(
        [post],
        sentiment_overview={"positive": 0.1, "neutral": 0.2, "negative": 0.7},
        community_distribution={"r/test": "100%"},
    )
    assert "高频信号词" in summary
    assert "情绪" in summary
    assert "r/test" in summary


def _make_service() -> HotpostService:
    settings = Settings(environment="test", allow_mock_fallback=True)
    return HotpostService(
        settings=settings,
        db=AsyncMock(),
        redis_client=AsyncMock(),
        reddit_client=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_maybe_llm_summary_low_confidence_marks_fallback() -> None:
    service = _make_service()
    post = Hotpost(
        rank=1,
        id="p1",
        title="Too expensive and confusing",
        body_preview="body",
        score=10,
        num_comments=2,
        heat_score=14,
        rant_score=12.0,
        rant_signals=["expensive"],
        subreddit="r/test",
        author="user",
        reddit_url="https://www.reddit.com/r/test/comments/p1",
        created_utc=0.0,
        signals=["expensive", "confusing"],
        signal_score=12.0,
        top_comments=[],
    )

    result = await service._maybe_llm_summary(
        query="robot vacuum",
        posts=[post],
        confidence="low",
        sentiment_overview={"positive": 0.1, "neutral": 0.2, "negative": 0.7},
        community_distribution={"r/test": "100%"},
    )

    assert result.source == "fallback"
    assert result.degraded_reason == "low_confidence"
    assert "高频信号词" in result.text


def test_build_debug_info_returns_stable_contract() -> None:
    debug = HotpostService._build_debug_info(
        resolution_source="llm",
        resolution_reason="llm_generate_failed",
        search_query="robot vacuum",
        query_parts=["robot vacuum", "roborock"],
        keywords=["robot", "vacuum"],
        time_filter="month",
        sort="top",
        subreddits=["r/robotvacuums"],
        raw_posts=15,
        filtered_posts=8,
        relevance_filtered=3,
        summary_result=HotpostSummaryResult(
            text="summary",
            source="fallback",
            degraded_reason="low_confidence",
        ),
        report_result=HotpostLLMReportResult(
            report=None,
            source="disabled",
            degraded_reason="missing_api_key",
        ),
        degraded_reasons=["llm_generate_failed", "low_confidence"],
        response_source="live",
    )

    assert debug.query_source == "llm"
    assert debug.query_degraded_reason == "llm_generate_failed"
    assert debug.search_query == "robot vacuum"
    assert debug.subreddits == ["r/robotvacuums"]
    assert debug.summary_source == "fallback"
    assert debug.summary_degraded_reason == "low_confidence"
    assert debug.report_source == "disabled"
    assert debug.report_degraded_reason == "missing_api_key"
    assert debug.llm_report_applied is False
    assert debug.degraded_reasons == ["llm_generate_failed", "low_confidence"]
