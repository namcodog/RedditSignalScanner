from __future__ import annotations

import pytest

from app.services.hotpost.hot_comment_sample import (
    collect_hot_comment_sample,
    extract_reddit_post_id,
)


class _FakeRedditClient:
    def __init__(self, comments: list[dict]) -> None:
        self._comments = comments
        self.calls: list[dict[str, object]] = []

    async def fetch_post_comments(self, post_id: str, **kwargs: object) -> list[dict]:
        self.calls.append({"post_id": post_id, **kwargs})
        return list(self._comments)


def test_extract_reddit_post_id_from_reddit_comments_url() -> None:
    assert (
        extract_reddit_post_id(
            "https://www.reddit.com/r/OpenAI/comments/1abc23d/sam_altman_thread/"
        )
        == "1abc23d"
    )
    assert (
        extract_reddit_post_id("https://reddit.com/comments/zz999xy/anything")
        == "zz999xy"
    )
    assert extract_reddit_post_id("https://reddit.com/post-hot") is None


@pytest.mark.asyncio
async def test_collect_hot_comment_sample_filters_noise_and_dedupes() -> None:
    reddit = _FakeRedditClient(
        comments=[
            {"body": "deleted", "score": 12},
            {"body": "[deleted]", "score": 11},
            {"body": "太短", "score": 10},
            {
                "body": "这不是普通治安事件，已经明显带上了对 AI 行业人物的人身敌意。",
                "score": 20,
            },
            {
                "body": "这不是普通治安事件，已经明显带上了对 AI 行业人物的人身敌意。",
                "score": 18,
            },
            {
                "body": "我更担心这会不会把以后所有 AI 公司高管都推成情绪出口。",
                "score": 9,
            },
        ]
    )

    result = await collect_hot_comment_sample(
        {
            "card_id": "card-hot",
            "source_link": "https://www.reddit.com/r/OpenAI/comments/1abc23d/sam_altman_thread/",
        },
        reddit_client=reddit,
        limit=40,
        depth=2,
    )

    assert result["post_id"] == "1abc23d"
    assert result["fetch_status"] == "ok"
    assert result["sample_size"] == 2
    assert [item["body"] for item in result["sample_comments"]] == [
        "这不是普通治安事件，已经明显带上了对 AI 行业人物的人身敌意。",
        "我更担心这会不会把以后所有 AI 公司高管都推成情绪出口。",
    ]
    assert reddit.calls == [
        {
            "post_id": "1abc23d",
            "mode": "smart_shallow",
            "limit": 40,
            "depth": 2,
            "comment_timeout": 15.0,
        }
    ]


@pytest.mark.asyncio
async def test_collect_hot_comment_sample_marks_invalid_source_link() -> None:
    reddit = _FakeRedditClient(comments=[])

    result = await collect_hot_comment_sample(
        {
            "card_id": "card-hot",
            "source_link": "https://reddit.com/post-hot",
        },
        reddit_client=reddit,
    )

    assert result["post_id"] is None
    assert result["fetch_status"] == "invalid_source_link"
    assert result["sample_size"] == 0
    assert result["sample_comments"] == []
    assert reddit.calls == []
