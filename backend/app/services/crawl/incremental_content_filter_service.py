from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping, MutableMapping

from app.services.community.blacklist_loader import BlacklistConfig
from app.services.crawl.content_duplicate_service import (
    ContentDuplicateLookupDeps,
    ContentDuplicateLookupInput,
    find_content_duplicate,
)
from app.services.infrastructure.reddit_client import RedditPost

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class IncrementalSpamFilterInput:
    community_name: str
    posts: list[RedditPost]
    spam_filter_mode: str


@dataclass(slots=True)
class IncrementalSpamFilterDeps:
    blacklist: BlacklistConfig | None
    spam_categories: MutableMapping[str, str]
    spam_classifier: Callable[[RedditPost], str | None] | None = None


def classify_spam_post(
    post: RedditPost,
    *,
    blacklist: BlacklistConfig | None,
) -> str | None:
    text = f"{post.title or ''} {post.selftext or ''}"

    if blacklist and post.author and blacklist.is_author_blacklisted(post.author):
        return "Spam_Bot"

    if post.title == "[placeholder missing post]":
        return "Spam_LowQuality"
    if post.selftext and "Welcome to" in post.selftext and "AmazonFC" in post.selftext:
        return "Spam_Bot"

    if blacklist and blacklist.matches_spam_pattern(text):
        if re.search(r"\b(btc|eth|crypto|token)\b", text, flags=re.IGNORECASE):
            return "Spam_Crypto"
        return "Spam_Ad"

    if blacklist and blacklist.should_filter_post(post.title or "", post.selftext or ""):
        return "Spam_LowQuality"

    return None


def filter_incremental_spam_posts(
    filter_input: IncrementalSpamFilterInput,
    deps: IncrementalSpamFilterDeps,
) -> list[RedditPost]:
    if filter_input.spam_filter_mode == "allow":
        return filter_input.posts

    classifier = deps.spam_classifier or (
        lambda post: classify_spam_post(post, blacklist=deps.blacklist)
    )
    valid_posts: list[RedditPost] = []
    for post in filter_input.posts:
        spam_category = classifier(post)
        if spam_category:
            if filter_input.spam_filter_mode == "drop":
                logger.warning(
                    "🚫 [SPAM BLOCKED] %s %s in %s: %s...",
                    spam_category,
                    post.id,
                    filter_input.community_name,
                    (post.title or "")[:40],
                )
                continue
            try:
                setattr(post, "spam_category", spam_category)
            except Exception:
                deps.spam_categories[str(post.id)] = spam_category
            logger.warning(
                "⚠️ [SPAM TAGGED] %s %s in %s: %s...",
                spam_category,
                post.id,
                filter_input.community_name,
                (post.title or "")[:40],
            )
        valid_posts.append(post)
    return valid_posts


@dataclass(slots=True)
class IncrementalDuplicateLookupDeps:
    text_norm_hash_available: Callable[[], Awaitable[bool]]
    execute_query: Callable[[Any, Mapping[str, Any]], Awaitable[Any]]


async def find_incremental_content_duplicate(
    *,
    subreddit: str,
    post: RedditPost,
    deps: IncrementalDuplicateLookupDeps,
) -> str | None:
    return await find_content_duplicate(
        lookup_input=ContentDuplicateLookupInput(
            subreddit=subreddit,
            title=post.title,
            body=post.selftext,
        ),
        deps=ContentDuplicateLookupDeps(
            text_norm_hash_available=deps.text_norm_hash_available,
            execute_query=deps.execute_query,
        ),
    )


__all__ = [
    "IncrementalDuplicateLookupDeps",
    "IncrementalSpamFilterDeps",
    "IncrementalSpamFilterInput",
    "classify_spam_post",
    "filter_incremental_spam_posts",
    "find_incremental_content_duplicate",
]
