from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.crawl.incremental_content_filter_service import (
    IncrementalDuplicateLookupDeps,
    IncrementalSpamFilterDeps,
    IncrementalSpamFilterInput,
    classify_spam_post,
    filter_incremental_spam_posts,
    find_incremental_content_duplicate,
)
from app.services.infrastructure.reddit_client import RedditPost


class _StubBlacklist:
    def __init__(
        self,
        *,
        author_blacklisted: bool = False,
        matches_spam_pattern: bool = False,
        should_filter_post: bool = False,
    ) -> None:
        self._author_blacklisted = author_blacklisted
        self._matches_spam_pattern = matches_spam_pattern
        self._should_filter_post = should_filter_post

    def is_author_blacklisted(self, _author: str) -> bool:
        return self._author_blacklisted

    def matches_spam_pattern(self, _text: str) -> bool:
        return self._matches_spam_pattern

    def should_filter_post(self, _title: str, _body: str) -> bool:
        return self._should_filter_post


def _post(
    *,
    post_id: str = "p1",
    title: str = "title",
    body: str = "body",
    author: str = "author",
) -> RedditPost:
    return RedditPost(
        id=post_id,
        title=title,
        selftext=body,
        score=1,
        num_comments=1,
        created_utc=0.0,
        subreddit="r/test",
        author=author,
        url="https://reddit.com/r/test/comments/p1",
        permalink="/r/test/comments/p1",
    )


def test_classify_spam_post_detects_blacklisted_author() -> None:
    result = classify_spam_post(
        _post(author="spam-author"),
        blacklist=_StubBlacklist(author_blacklisted=True),
    )

    assert result == "Spam_Bot"


def test_classify_spam_post_detects_crypto_spam() -> None:
    result = classify_spam_post(
        _post(title="Buy BTC now", body="crypto token pump"),
        blacklist=_StubBlacklist(matches_spam_pattern=True),
    )

    assert result == "Spam_Crypto"


def test_filter_incremental_spam_posts_drops_spam_posts() -> None:
    kept = filter_incremental_spam_posts(
        IncrementalSpamFilterInput(
            community_name="r/test",
            posts=[_post(post_id="keep"), _post(post_id="drop")],
            spam_filter_mode="drop",
        ),
        IncrementalSpamFilterDeps(
            blacklist=None,
            spam_categories={},
            spam_classifier=lambda post: "Spam_Ad" if post.id == "drop" else None,
        ),
    )

    assert [post.id for post in kept] == ["keep"]


def test_filter_incremental_spam_posts_tags_when_slots_block_setattr() -> None:
    spam_categories: dict[str, str] = {}

    kept = filter_incremental_spam_posts(
        IncrementalSpamFilterInput(
            community_name="r/test",
            posts=[_post(post_id="tagged")],
            spam_filter_mode="tag",
        ),
        IncrementalSpamFilterDeps(
            blacklist=None,
            spam_categories=spam_categories,
            spam_classifier=lambda _post: "Spam_Ad",
        ),
    )

    assert [post.id for post in kept] == ["tagged"]
    assert spam_categories == {"tagged": "Spam_Ad"}


@pytest.mark.asyncio
async def test_find_incremental_content_duplicate_returns_source_post_id() -> None:
    async def _execute_query(*_args, **_kwargs):
        return SimpleNamespace(first=lambda: ("existing-post",))

    result = await find_incremental_content_duplicate(
        subreddit="r/test",
        post=_post(title="duplicate", body="same text"),
        deps=IncrementalDuplicateLookupDeps(
            text_norm_hash_available=AsyncMock(return_value=True),
            execute_query=_execute_query,
        ),
    )

    assert result == "existing-post"
