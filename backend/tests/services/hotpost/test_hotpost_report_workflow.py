from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.schemas.hotpost import Hotpost, HotpostComment
from app.services.hotpost.report_workflow import (
    HotpostReportWorkflowDeps,
    HotpostReportWorkflowInput,
    build_hotpost_report_result,
)
from app.services.hotpost.result_meta import HotpostLLMReportResult


def _build_post() -> Hotpost:
    return Hotpost(
        rank=1,
        id="p1",
        title="Best robot vacuum",
        body_preview="body",
        score=42,
        num_comments=5,
        heat_score=52,
        rant_score=0.0,
        rant_signals=[],
        subreddit="r/robotvacuums",
        author="user",
        reddit_url="https://reddit.com/p1",
        created_utc=0.0,
        signals=["hidden gem"],
        signal_score=12.0,
        top_comments=[],
    )


def _build_comment() -> HotpostComment:
    return HotpostComment(
        comment_fullname="t1_c1",
        author="commenter",
        body="me too",
        score=3,
        permalink="/r/robotvacuums/comments/p1/_/c1",
    )


@pytest.mark.asyncio
async def test_hotpost_report_workflow_returns_disabled_when_flag_off() -> None:
    result = await build_hotpost_report_result(
        workflow_input=HotpostReportWorkflowInput(
            mode="trending",
            query="robot vacuum",
            time_filter="all",
            top_posts=[_build_post()],
            all_comments=[_build_comment()],
            llm_model_name="gpt-test",
        ),
        deps=HotpostReportWorkflowDeps(
            getenv=lambda key, default="": "false" if key == "ENABLE_HOTPOST_LLM_REPORT" else default,
        ),
    )

    assert result.source == "disabled"
    assert result.degraded_reason == "report_llm_disabled"


@pytest.mark.asyncio
async def test_hotpost_report_workflow_returns_missing_api_key_when_not_configured() -> None:
    result = await build_hotpost_report_result(
        workflow_input=HotpostReportWorkflowInput(
            mode="trending",
            query="robot vacuum",
            time_filter="all",
            top_posts=[_build_post()],
            all_comments=[_build_comment()],
            llm_model_name="gpt-test",
        ),
        deps=HotpostReportWorkflowDeps(
            resolve_api_key=lambda: None,
            getenv=lambda _key, default="": default,
        ),
    )

    assert result.source == "disabled"
    assert result.degraded_reason == "missing_api_key"


@pytest.mark.asyncio
async def test_hotpost_report_workflow_builds_payload_and_calls_generator() -> None:
    fake_generate = AsyncMock(
        return_value=HotpostLLMReportResult(report={"headline": "x"}, source="llm")
    )

    result = await build_hotpost_report_result(
        workflow_input=HotpostReportWorkflowInput(
            mode="trending",
            query="robot vacuum",
            time_filter="all",
            top_posts=[_build_post()],
            all_comments=[_build_comment()],
            llm_model_name="gpt-test",
        ),
        deps=HotpostReportWorkflowDeps(
            resolve_api_key=lambda: "token",
            client_factory=lambda _model: object(),
            generate_report=fake_generate,
            getenv=lambda key, default="": {
                "ENABLE_HOTPOST_LLM_REPORT": "true",
                "HOTPOST_LLM_MAX_TOKENS": "2048",
                "HOTPOST_LLM_TEMPERATURE": "0.2",
            }.get(key, default),
        ),
    )

    assert result.source == "llm"
    kwargs = fake_generate.await_args.kwargs
    assert kwargs["mode"] == "trending"
    assert kwargs["query"] == "robot vacuum"
    assert kwargs["time_filter"] == "all"
    assert kwargs["max_tokens"] == 2048
    assert kwargs["temperature"] == 0.2
    assert kwargs["posts_data"][0]["id"] == "p1"
    assert kwargs["comments_data"][0]["body"] == "me too"
