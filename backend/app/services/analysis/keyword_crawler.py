from __future__ import annotations

import re
from itertools import islice
from typing import Dict, List, Sequence

from app.services.reddit_client import RedditAPIClient, RedditPost


def _extract_candidate_terms(description: str) -> List[str]:
    tokens = re.findall(r"[A-Za-z]{3,}", description.lower())
    seen: set[str] = set()
    ordered: List[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _build_queries(
    base_keywords: Sequence[str],
    derived_tokens: Sequence[str],
    query_variants: int,
) -> List[str]:
    tokens = [kw.lower() for kw in base_keywords if kw]
    tokens.extend(t for t in derived_tokens if t not in tokens)
    if not tokens:
        return []

    queries: List[str] = []
    window = max(2, min(4, len(tokens)))
    for idx in range(query_variants):
        start = idx * (window // 2)
        slice_tokens = list(islice(tokens, start, start + window))
        if not slice_tokens:
            break
        queries.append(" ".join(slice_tokens))
    if not queries:
        queries.append(" ".join(tokens[:window]))
    return queries[:query_variants]


def _normalise_post(post: RedditPost | Dict[str, object]) -> Dict[str, object]:
    if isinstance(post, dict):
        return {
            "id": post.get("id", ""),
            "title": post.get("title", ""),
            "summary": post.get("selftext") or post.get("summary", ""),
            "score": post.get("score", 0),
            "num_comments": post.get("num_comments", 0),
            "subreddit": post.get("subreddit", ""),
            "author": post.get("author", "unknown"),
            "url": post.get("url"),
            "permalink": post.get("permalink"),
            "source_type": post.get("source_type", "search"),
            "created_utc": post.get("created_utc", 0.0),
        }

    return {
        "id": post.id,
        "title": post.title,
        "summary": post.selftext or "",
        "score": post.score,
        "num_comments": post.num_comments,
        "subreddit": post.subreddit,
        "author": post.author,
        "url": post.url,
        "permalink": post.permalink,
        "source_type": "search",
        "created_utc": post.created_utc,
    }


async def keyword_crawl(
    client: RedditAPIClient,
    *,
    product_description: str,
    base_keywords: Sequence[str],
    per_query_limit: int = 25,
    query_variants: int = 3,
    time_filter: str = "month",
    sort: str = "relevance",
) -> List[Dict[str, object]]:
    """
    Fetch supplementary Reddit posts using keyword search for sample backfill.
    """
    derived_tokens = _extract_candidate_terms(product_description)
    queries = _build_queries(base_keywords, derived_tokens, query_variants)
    if not queries:
        return []

    collected: Dict[str, Dict[str, object]] = {}
    for query in queries:
        results = await client.search_posts(
            query,
            limit=per_query_limit,
            time_filter=time_filter,
            sort=sort,
        )
        for post in results:
            normalised = _normalise_post(post)
            post_id: str = str(normalised["id"])
            collected.setdefault(post_id, normalised)
    return list(collected.values())


__all__ = ["keyword_crawl"]
