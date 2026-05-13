from __future__ import annotations

import pytest

from app.schemas.hotpost import Hotpost
from app.services.hotpost.summary_workflow import (
    HotpostSummaryWorkflowDeps,
    HotpostSummaryWorkflowInput,
    build_hotpost_fallback_summary,
    generate_hotpost_summary,
)


def _post() -> Hotpost:
    return Hotpost(
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


def test_build_hotpost_fallback_summary_includes_signals_and_sentiment() -> None:
    summary = build_hotpost_fallback_summary(
        [_post()],
        sentiment_overview={"positive": 0.1, "neutral": 0.2, "negative": 0.7},
        community_distribution={"r/test": "100%"},
    )
    assert "高频信号词" in summary
    assert "情绪" in summary
    assert "r/test" in summary


class _FakeClient:
    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        return "一句洞察"


@pytest.mark.asyncio
async def test_generate_hotpost_summary_low_confidence_marks_fallback() -> None:
    result = await generate_hotpost_summary(
        workflow_input=HotpostSummaryWorkflowInput(
            query="robot vacuum",
            posts=[_post()],
            confidence="low",
            sentiment_overview={"positive": 0.1, "neutral": 0.2, "negative": 0.7},
            community_distribution={"r/test": "100%"},
        ),
        deps=HotpostSummaryWorkflowDeps(
            resolve_api_key=lambda: "test-key",
            client_factory=lambda: _FakeClient(),
        ),
    )

    assert result.source == "fallback"
    assert result.degraded_reason == "low_confidence"
    assert "高频信号词" in result.text


@pytest.mark.asyncio
async def test_generate_hotpost_summary_returns_llm_text_when_available() -> None:
    result = await generate_hotpost_summary(
        workflow_input=HotpostSummaryWorkflowInput(
            query="robot vacuum",
            posts=[_post()],
            confidence="high",
            sentiment_overview={"positive": 0.1, "neutral": 0.2, "negative": 0.7},
            community_distribution={"r/test": "100%"},
        ),
        deps=HotpostSummaryWorkflowDeps(
            resolve_api_key=lambda: "test-key",
            client_factory=lambda: _FakeClient(),
        ),
    )

    assert result.source == "llm"
    assert result.text == "一句洞察"
