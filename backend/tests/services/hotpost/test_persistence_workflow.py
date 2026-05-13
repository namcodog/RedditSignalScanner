from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.hotpost import Hotpost, HotpostComment, HotpostSearchResponse
from app.services.hotpost.persistence_workflow import (
    HotpostPersistenceWorkflowDeps,
    HotpostPersistenceWorkflowInput,
    persist_hotpost_search_side_effects,
)
from app.services.hotpost.result_meta import HotpostLLMReportResult


def _comment(fullname: str, *, score: int = 3) -> HotpostComment:
    return HotpostComment(
        comment_fullname=fullname,
        author="user",
        body=f"body-{fullname}",
        score=score,
        permalink=f"/r/test/comments/p1/{fullname}",
    )


def _post(post_id: str, subreddit: str, *, comments: list[HotpostComment]) -> Hotpost:
    return Hotpost(
        rank=1,
        id=post_id,
        title=f"title-{post_id}",
        body_preview="preview",
        score=12,
        num_comments=len(comments),
        heat_score=20,
        rant_score=10.0,
        rant_signals=["expensive"],
        subreddit=subreddit,
        author="author",
        reddit_url=f"https://www.reddit.com/r/test/comments/{post_id}",
        created_utc=0.0,
        signals=["expensive"],
        signal_score=10.0,
        top_comments=comments,
    )


def _response(posts: list[Hotpost]) -> HotpostSearchResponse:
    return HotpostSearchResponse(
        query_id=str(uuid.uuid4()),
        query="robot vacuum",
        mode="rant",
        search_time=datetime.now(timezone.utc),
        from_cache=False,
        status="completed",
        summary="summary",
        markdown_report=None,
        top_posts=posts,
        key_comments=[comment for post in posts for comment in post.top_comments],
        pain_points=[],
        communities=sorted({post.subreddit for post in posts}),
        related_queries=[],
        evidence_count=len(posts),
        community_distribution={"r/test": "100%"},
        sentiment_overview={"positive": 0.1, "neutral": 0.2, "negative": 0.7},
        confidence="high",
        notes=[],
    )


@pytest.mark.asyncio
async def test_persist_hotpost_search_side_effects_persists_evidence_comments_and_cache() -> None:
    posts = [
        _post("p1", "r/test", comments=[_comment("t1_a"), _comment("t1_b", score=8)]),
        _post("p2", "r/test", comments=[_comment("t1_c", score=5)]),
    ]
    response = _response(posts)
    query_id = uuid.uuid4()

    db = AsyncMock()
    redis = AsyncMock()
    upsert = AsyncMock(
        side_effect=[SimpleNamespace(id=101), SimpleNamespace(id=102)]
    )
    insert_map = AsyncMock()
    discover = AsyncMock()
    update_query = AsyncMock()

    result = await persist_hotpost_search_side_effects(
        workflow_input=HotpostPersistenceWorkflowInput(
            query_id=query_id,
            request_query="robot vacuum",
            search_query="robot vacuum",
            keywords=["robot", "vacuum"],
            top_posts=posts,
            response=response,
            llm_report_result=HotpostLLMReportResult(
                report={"headline": "demo"},
                source="llm",
            ),
            cache_key="hotpost:cache:test",
            cache_ttl_seconds=600,
            comments_cache_ttl_seconds=7200,
            latency_ms=321,
            api_calls=4,
            subreddits=["r/test"],
        ),
        deps=HotpostPersistenceWorkflowDeps(
            db=db,
            redis_client=redis,
            upsert_evidence_post=upsert,
            insert_query_evidence_map=insert_map,
            maybe_discover_community=discover,
            update_hotpost_query=update_query,
        ),
    )

    assert result.evidence_count == 2
    assert result.community_count == 1
    assert result.comments_cache_entries == 2
    assert result.discovered_communities == 1

    assert upsert.await_count == 2
    insert_map.assert_any_await(
        db,
        query_id=query_id,
        evidence_id=101,
        rank=1,
        signal_score=10.0,
        signals=["expensive"],
        top_comment_refs=[
            {
                "comment_fullname": "t1_a",
                "permalink": "/r/test/comments/p1/t1_a",
                "score": 3,
            },
            {
                "comment_fullname": "t1_b",
                "permalink": "/r/test/comments/p1/t1_b",
                "score": 8,
            },
        ],
    )
    discover.assert_awaited_once_with(
        db,
        subreddit="r/test",
        evidence_count=2,
        query="robot vacuum",
        keywords=["robot", "vacuum"],
    )
    update_query.assert_awaited_once_with(
        db,
        query_id=query_id,
        evidence_count=2,
        community_count=1,
        confidence="high",
        from_cache=False,
        latency_ms=321,
        api_calls=4,
        subreddits=["r/test"],
    )

    cache_calls = redis.setex.await_args_list
    assert len(cache_calls) == 4

    comments_key, comments_ttl, comments_payload = cache_calls[0].args
    assert comments_key == f"hotpost:comments:{query_id}"
    assert comments_ttl == 7200
    decoded_comments = json.loads(comments_payload)
    assert sorted(decoded_comments.keys()) == ["101", "102"]

    llm_key = cache_calls[1].args[0]
    result_key = cache_calls[3].args[0]
    assert llm_key == f"hotpost:llm_report:{query_id}"
    assert result_key == f"hotpost:result:{query_id}"


@pytest.mark.asyncio
async def test_persist_hotpost_search_side_effects_skips_llm_report_cache_without_report() -> None:
    posts = [_post("p1", "r/test", comments=[_comment("t1_a")])]
    response = _response(posts)
    query_id = uuid.uuid4()

    db = AsyncMock()
    redis = AsyncMock()

    await persist_hotpost_search_side_effects(
        workflow_input=HotpostPersistenceWorkflowInput(
            query_id=query_id,
            request_query="robot vacuum",
            search_query="robot vacuum",
            keywords=["robot"],
            top_posts=posts,
            response=response,
            llm_report_result=HotpostLLMReportResult(report=None, source="disabled"),
            cache_key="hotpost:cache:test",
            cache_ttl_seconds=600,
            comments_cache_ttl_seconds=7200,
            latency_ms=123,
            api_calls=2,
            subreddits=None,
        ),
        deps=HotpostPersistenceWorkflowDeps(
            db=db,
            redis_client=redis,
            upsert_evidence_post=AsyncMock(return_value=SimpleNamespace(id=201)),
            insert_query_evidence_map=AsyncMock(),
            maybe_discover_community=AsyncMock(),
            update_hotpost_query=AsyncMock(),
        ),
    )

    cache_keys = [call.args[0] for call in redis.setex.await_args_list]
    assert f"hotpost:llm_report:{query_id}" not in cache_keys
    assert cache_keys == [
        f"hotpost:comments:{query_id}",
        "hotpost:cache:test",
        f"hotpost:result:{query_id}",
    ]
