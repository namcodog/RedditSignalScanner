from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pytest

from app.services.analysis.keyword_crawler import keyword_crawl


@dataclass
class _CapturedCall:
    query: str
    limit: int
    time_filter: str
    sort: str


class FakeRedditClient:
    def __init__(self, responses: List[dict]) -> None:
        self.responses = responses
        self.calls: list[_CapturedCall] = []

    async def search_posts(
        self,
        query: str,
        *,
        limit: int = 50,
        time_filter: str = "month",
        sort: str = "relevance",
    ) -> List[dict]:
        self.calls.append(
            _CapturedCall(
                query=query,
                limit=limit,
                time_filter=time_filter,
                sort=sort,
            )
        )
        return self.responses


@pytest.mark.asyncio
async def test_keyword_crawl_uses_description_keywords_for_queries() -> None:
    fake_posts = [
        {
            "id": "kw-1",
            "title": "Looking for an AI automation copilot",
            "selftext": "Need something to summarise weekly research threads.",
            "score": 120,
            "num_comments": 18,
            "created_utc": 0.0,
            "subreddit": "r/startups",
            "author": "tester",
            "url": "https://reddit.com/r/startups/kw-1",
            "permalink": "/r/startups/comments/kw-1",
        }
    ]
    client = FakeRedditClient(fake_posts)

    product_description = "AI note taking assistant that automates weekly research summaries for startup founders."
    results = await keyword_crawl(
        client,
        product_description=product_description,
        base_keywords=["ai", "automation"],
        per_query_limit=25,
        query_variants=2,
    )

    assert len(results) == len(fake_posts)
    assert all(post["source_type"] == "search" for post in results)
    assert client.calls, "Expected Reddit search to be invoked"
    # Ensure query contains meaningful tokens from description/keywords
    observed_queries = {call.query for call in client.calls}
    assert any("ai" in query.lower() for query in observed_queries)
    assert any("note" in query.lower() for query in observed_queries)
    assert all(call.limit == 25 for call in client.calls)
    assert all(call.time_filter == "month" for call in client.calls)
    assert all(call.sort == "relevance" for call in client.calls)
