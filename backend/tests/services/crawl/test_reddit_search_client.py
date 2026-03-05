import asyncio
from types import SimpleNamespace

import pytest

from app.services.infrastructure.reddit_client import RedditAPIClient, RedditPost


@pytest.mark.asyncio
async def test_search_subreddit_page_builds_params(monkeypatch):
    client = RedditAPIClient(
        client_id="id",
        client_secret="secret",
        user_agent="ua",
        rate_limit=2,
        rate_limit_window=1.0,
        max_concurrency=1,
    )

    # Stub authenticate
    async def _auth():
        client.access_token = "tok"
        return None

    monkeypatch.setattr(client, "authenticate", _auth)

    captured = {}

    async def fake_request(method, url, headers=None, params=None, data=None):
        captured["url"] = url
        captured["params"] = params
        # Return one post and an after token
        return {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "abc",
                            "title": "t",
                            "selftext": "s",
                            "score": 1,
                            "num_comments": 0,
                            "created_utc": 1700000000.0,
                            "subreddit": "ecommerce",
                            "author": "u",
                            "url": "u",
                            "permalink": "/r/ecommerce/abc",
                        }
                    }
                ],
                "after": "t3_xyz",
            }
        }

    monkeypatch.setattr(client, "_request_json", fake_request)

    posts, after = await client.search_subreddit_page(
        "ecommerce",
        query="timestamp:1..2",
        sort="new",
        limit=100,
        time_filter="all",
        restrict_sr=1,
        syntax="cloudsearch",
    )

    assert captured["url"].endswith("/r/ecommerce/search")
    assert captured["params"]["restrict_sr"] == "1"
    assert captured["params"]["syntax"] == "cloudsearch"
    assert after == "t3_xyz"
    assert posts and posts[0].id == "abc"

