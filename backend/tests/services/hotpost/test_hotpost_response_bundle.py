from __future__ import annotations

from app.schemas.hotpost import Hotpost, HotpostComment
from app.services.hotpost.keywords import load_default_hotpost_keywords
from app.services.hotpost.response_bundle import (
    HotpostResponseBundleInput,
    build_hotpost_search_response,
    resolve_hotpost_response,
)
from app.services.hotpost.result_meta import HotpostLLMReportResult, HotpostSummaryResult


def _post(*, idx: int, subreddit: str = "r/test") -> Hotpost:
    return Hotpost(
        rank=idx,
        id=f"p{idx}",
        title=f"Too expensive and confusing {idx}",
        body_preview="body",
        score=10 + idx,
        num_comments=2,
        heat_score=14,
        rant_score=12.0,
        rant_signals=["expensive"],
        subreddit=subreddit,
        author="user",
        reddit_url=f"https://www.reddit.com/r/test/comments/p{idx}",
        created_utc=0.0,
        signals=["expensive", "confusing"],
        signal_score=12.0,
        top_comments=[],
    )


def _comment(*, idx: int) -> HotpostComment:
    return HotpostComment(
        comment_fullname=f"t1_{idx}",
        author="user",
        body=f"comment {idx}",
        score=idx,
        permalink=f"/r/test/comments/p1/_/{idx}",
    )


def test_resolve_hotpost_response_ignores_disabled_report_reason() -> None:
    status, degraded = resolve_hotpost_response(
        resolution_reason="llm_generate_failed",
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
    )

    assert status == "degraded"
    assert degraded == ["llm_generate_failed", "low_confidence"]


def test_build_hotpost_search_response_builds_typed_rant_response() -> None:
    response = build_hotpost_search_response(
        HotpostResponseBundleInput(
            query_id="qid-1",
            query="robot vacuum",
            mode="rant",
            top_posts=[_post(idx=1)],
            all_comments=[_comment(idx=1), _comment(idx=2)],
            notes=["关键词过长，已拆分为 2 次查询"],
            resolution_source="llm",
            resolution_reason="llm_generate_failed",
            search_query="robot vacuum",
            query_parts=["robot vacuum", "roborock"],
            keywords=["robot", "vacuum"],
            time_filter="month",
            sort="top",
            subreddits=["r/robotvacuums"],
            raw_posts=12,
            filtered_posts=1,
            relevance_filtered=3,
            summary_result=HotpostSummaryResult(
                text="fallback summary",
                source="fallback",
                degraded_reason="low_confidence",
            ),
            report_result=HotpostLLMReportResult(
                report=None,
                source="disabled",
                degraded_reason="missing_api_key",
            ),
            sentiment_overview={"positive": 0.1, "neutral": 0.2, "negative": 0.7},
            confidence="low",
            lexicon=load_default_hotpost_keywords(),
            pain_points=[],
            categories=["Home_Lifestyle"],
        )
    )

    assert response.status == "degraded"
    assert response.debug_info is not None
    assert response.debug_info.query_source == "llm"
    assert response.debug_info.summary_source == "fallback"
    assert response.debug_info.report_source == "disabled"
    assert response.reliability_note is not None
    assert "样本量 1 条" in response.reliability_note
    assert response.next_steps is not None
    assert response.next_steps.deepdive_available is True
    assert response.top_rants is not None
    assert response.migration_intent is not None


def test_build_hotpost_search_response_enriches_opportunity_strength() -> None:
    posts = [_post(idx=i, subreddit="r/opportunity") for i in range(1, 11)]
    response = build_hotpost_search_response(
        HotpostResponseBundleInput(
            query_id="qid-2",
            query="robot vacuum",
            mode="opportunity",
            top_posts=posts,
            all_comments=[_comment(idx=i) for i in range(1, 6)],
            notes=[],
            resolution_source="rule",
            resolution_reason=None,
            search_query="robot vacuum",
            query_parts=["robot vacuum"],
            keywords=["robot", "vacuum"],
            time_filter="month",
            sort="top",
            subreddits=["r/robotvacuums"],
            raw_posts=20,
            filtered_posts=10,
            relevance_filtered=5,
            summary_result=HotpostSummaryResult(text="summary", source="llm"),
            report_result=HotpostLLMReportResult(report=None, source="disabled"),
            sentiment_overview={"positive": 0.3, "neutral": 0.3, "negative": 0.4},
            confidence="medium",
            lexicon=load_default_hotpost_keywords(),
            me_too_count=5,
            opportunities=[{"summary": "用户在讨论中表达了需求缺口", "me_too_count": 5}],
        )
    )

    assert response.status == "completed"
    assert response.opportunity_strength == "medium"
    assert response.top_discovery_posts is not None
    assert response.unmet_needs is not None
    assert response.unmet_needs[0].need == "用户在讨论中表达了需求缺口"
