from __future__ import annotations

import httpx
import pytest

from app.services.infrastructure.reddit_client import RedditAPIError
from app.services.infrastructure.sociavault_reddit_client import (
    SociaVaultRedditClient,
    _flatten_sociavault_comments,
    _normalize_sociavault_posts,
)


def test_normalize_sociavault_posts_maps_search_payload() -> None:
    payload = {
        "data": {
            "posts": {
                "0": {
                    "post_id": "t3_abc123",
                    "title": "OpenAI is in big trouble",
                    "permalink": "/r/OpenAI/comments/abc123/openai_is_in_big_trouble/",
                    "subreddit": {"name": "OpenAI"},
                    "votes": 3251,
                    "num_comments": 451,
                    "created_at": 1775924794,
                }
            }
        }
    }

    posts = _normalize_sociavault_posts(payload)

    assert len(posts) == 1
    assert posts[0].id == "abc123"
    assert posts[0].subreddit == "OpenAI"
    assert posts[0].score == 3251


def test_flatten_sociavault_comments_flattens_nested_replies() -> None:
    payload = {
        "data": {
            "comments": {
                "0": {
                    "id": "c1",
                    "body": "top comment",
                    "score": 10,
                    "author": "alice",
                    "url": "/r/OpenAI/comments/abc123/x/c1/",
                    "replies": {
                        "items": {
                            "0": {
                                "id": "c2",
                                "body": "reply",
                                "score": 3,
                                "author": "bob",
                                "url": "/r/OpenAI/comments/abc123/x/c2/",
                            }
                        }
                    },
                }
            }
        }
    }

    comments = _flatten_sociavault_comments(payload, limit=10)

    assert [item["id"] for item in comments] == ["c1", "c2"]


@pytest.mark.asyncio
async def test_sociavault_request_json_maps_timeout_to_reddit_api_error() -> None:
    client = SociaVaultRedditClient(api_key="k", base_url="https://api.sociavault.com/v1")

    class _TimeoutingClient:
        async def get(self, *args, **kwargs):
            raise httpx.ReadTimeout("timeout")

    client._client = _TimeoutingClient()

    with pytest.raises(RedditAPIError, match="SociaVault Reddit request timed out"):
        await client._request_json("/scrape/reddit/post/comments", params={"url": "https://reddit.com"})
