from __future__ import annotations

from app.schemas.hotpost import Hotpost
from app.services.hotpost.service import HotpostService


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
