from __future__ import annotations

import asyncio
import re
from collections import Counter
from typing import Any, Awaitable, Callable

from app.services.hotpost.detail_builder import compute_need_urgency, compute_rant_intensity
from app.services.hotpost.keywords import HotpostLexicon
from app.services.hotpost.rules import (
    compute_signal_score,
    detect_discovery_signals,
    detect_opportunity_signals,
    detect_rant_signals,
    normalize_text,
)
from app.services.hotpost.summary_workflow import (
    HotpostSummaryWorkflowDeps,
    HotpostSummaryWorkflowInput,
    build_hotpost_fallback_summary,
    generate_hotpost_summary,
)
from app.services.infrastructure.reddit_client import RedditPost
from app.services.llm.clients.openai_client import OpenAIChatClient, resolve_llm_api_key
from app.schemas.hotpost import Hotpost, HotpostSearchRequest, PainPoint
from app.utils.url import normalize_reddit_url


def resolve_hotpost_mode(request: HotpostSearchRequest) -> str:
    if request.mode:
        return request.mode
    query = request.query.lower()
    rant_hints = ["口碑", "吐槽", "差评", "complaint", "rant", "issue", "problem", "broken", "hate"]
    opp_hints = ["推荐", "有没有", "替代", "recommend", "alternative", "looking for", "need", "best"]
    if any(h in query for h in rant_hints):
        return "rant"
    if any(h in query for h in opp_hints):
        return "opportunity"
    return "trending"


def split_hotpost_search_queries(search_query: str, *, max_chars: int) -> list[str]:
    cleaned = " ".join((search_query or "").strip().split())
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    parts = re.split(r"\s+OR\s+", cleaned, flags=re.IGNORECASE)
    if len(parts) > 1:
        chunks: list[str] = []
        current: list[str] = []
        for part in parts:
            if not part:
                continue
            candidate = " OR ".join(current + [part]) if current else part
            if len(candidate) > max_chars and current:
                chunks.append(" OR ".join(current))
                current = [part]
            else:
                current.append(part)
        if current:
            chunks.append(" OR ".join(current))
        return chunks

    words = cleaned.split()
    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word]) if current else word
        if len(candidate) > max_chars and current:
            chunks.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        chunks.append(" ".join(current))
    return chunks


def resolve_hotpost_time_filter(mode: str, request: HotpostSearchRequest) -> str:
    if request.time_filter:
        return request.time_filter
    if mode == "rant":
        return "all"
    if mode == "opportunity":
        return "month"
    return "all"


def resolve_hotpost_sort(mode: str) -> str:
    if mode == "opportunity":
        return "relevance"
    if mode == "trending":
        return "top"
    return "top"


async def acquire_hotpost_rate_budget(
    *,
    cost: int,
    rate_limiter: Any,
    queue_tracker: Any | None = None,
) -> None:
    wait_seconds = await rate_limiter.acquire(cost=cost)
    if wait_seconds > 0:
        if queue_tracker is not None:
            await queue_tracker.mark_waiting(estimated_wait_seconds=wait_seconds)
        await asyncio.sleep(float(wait_seconds))
        if queue_tracker is not None:
            await queue_tracker.mark_processing()


async def search_hotpost_subreddit_posts(
    subreddit: str,
    query: str,
    *,
    sort: str,
    time_filter: str,
    max_posts: int,
    queue_tracker: Any | None,
    acquire_rate_budget: Callable[..., Awaitable[None]],
    search_subreddit_page: Callable[..., Awaitable[tuple[list[RedditPost], str | None]]],
) -> tuple[list[RedditPost], int]:
    posts: list[RedditPost] = []
    after: str | None = None
    calls = 0
    while len(posts) < max_posts:
        await acquire_rate_budget(cost=1, queue_tracker=queue_tracker)
        batch, after = await search_subreddit_page(
            subreddit,
            query,
            limit=min(100, max_posts - len(posts)),
            sort=sort,
            time_filter=time_filter,
            after=after,
        )
        posts.extend(batch)
        calls += 1
        if not after:
            break
    return posts, calls


async def fetch_hotpost_comments(
    post_id: str,
    *,
    queue_tracker: Any | None,
    acquire_rate_budget: Callable[..., Awaitable[None]],
    fetch_post_comments: Callable[..., Awaitable[list[dict[str, Any]]]],
) -> list[dict[str, Any]]:
    await acquire_rate_budget(cost=1, queue_tracker=queue_tracker)
    comments = await fetch_post_comments(
        post_id,
        sort="top",
        depth=1,
        limit=3,
        mode="topn",
    )
    trimmed: list[dict[str, Any]] = []
    for raw in comments[:3]:
        payload = dict(raw)
        body = str(payload.get("body") or "")
        payload["body"] = body[:400]
        trimmed.append(payload)
    return trimmed


def select_hotpost_signals(
    mode: str,
    text: str,
    *,
    lexicon: HotpostLexicon,
) -> dict[str, list[str]]:
    if mode == "rant":
        return detect_rant_signals(text, lexicon)
    if mode == "opportunity":
        return detect_opportunity_signals(text, lexicon)
    return detect_discovery_signals(text, lexicon)


def resolve_hotpost_sentiment_label(
    mode: str,
    text: str,
    signals: dict[str, list[str]],
    *,
    lexicon: HotpostLexicon,
) -> str:
    if mode == "rant":
        if signals.get("strong") or signals.get("medium"):
            return "negative"
        return "neutral"
    discovery = detect_discovery_signals(text, lexicon)
    if discovery.get("positive"):
        return "positive"
    return "neutral"


def build_hotpost_post(
    post: RedditPost,
    *,
    rank: int,
    signals: dict[str, list[str]],
) -> Hotpost:
    signal_score = compute_signal_score(signals, score=post.score, num_comments=post.num_comments)
    reddit_url = normalize_reddit_url(post.url, post.permalink)
    heat_score = post.score + post.num_comments * 2
    return Hotpost(
        rank=rank,
        id=post.id,
        title=post.title,
        body_preview=(post.selftext or "")[:500],
        score=post.score,
        num_comments=post.num_comments,
        heat_score=heat_score,
        rant_score=signal_score,
        rant_signals=[s for group in signals.values() for s in group],
        subreddit=post.subreddit,
        author=post.author,
        reddit_url=reddit_url,
        created_utc=post.created_utc,
        signals=[s for group in signals.values() for s in group],
        signal_score=signal_score,
        top_comments=[],
    )


def build_hotpost_pain_points(posts: list[Hotpost], categories: list[str]) -> list[PainPoint]:
    counter = Counter(categories)
    points: list[PainPoint] = []
    for category, mentions in counter.most_common(5):
        sample_posts = [p for p in posts if p.subreddit and p.title and p.title]
        urls = [p.reddit_url for p in posts[:3]]
        severity = "high" if mentions >= 10 else "medium" if mentions >= 5 else "low"
        points.append(
            PainPoint(
                category=category,
                description=f"用户频繁提及 {category} 相关问题",
                mentions=mentions,
                severity=severity,
                sample_quotes=[p.title for p in sample_posts[:2]],
                evidence_urls=urls,
            )
        )
    return points


def resolve_hotpost_confidence_level(evidence_count: int) -> str:
    if evidence_count <= 0:
        return "none"
    if evidence_count >= 20:
        return "high"
    if evidence_count >= 10:
        return "medium"
    return "low"


async def maybe_build_hotpost_llm_summary(
    *,
    query: str,
    posts: list[Hotpost],
    confidence: str,
    sentiment_overview: dict[str, float] | None = None,
    community_distribution: dict[str, str] | None = None,
    llm_model_name: str,
) -> Any:
    return await generate_hotpost_summary(
        workflow_input=HotpostSummaryWorkflowInput(
            query=query,
            posts=posts,
            confidence=confidence,
            sentiment_overview=sentiment_overview,
            community_distribution=community_distribution,
        ),
        deps=HotpostSummaryWorkflowDeps(
            resolve_api_key=resolve_llm_api_key,
            client_factory=lambda: OpenAIChatClient(model=llm_model_name),
        ),
    )


def build_hotpost_fallback_text(
    posts: list[Hotpost],
    *,
    sentiment_overview: dict[str, float] | None = None,
    community_distribution: dict[str, str] | None = None,
) -> str:
    return build_hotpost_fallback_summary(
        posts,
        sentiment_overview=sentiment_overview,
        community_distribution=community_distribution,
    )


def build_hotpost_opportunity_meta(
    posts: list[Hotpost],
) -> tuple[float | None, float | None]:
    return compute_rant_intensity(posts), compute_need_urgency(posts)


__all__ = [
    "acquire_hotpost_rate_budget",
    "build_hotpost_fallback_text",
    "build_hotpost_opportunity_meta",
    "build_hotpost_pain_points",
    "build_hotpost_post",
    "fetch_hotpost_comments",
    "maybe_build_hotpost_llm_summary",
    "resolve_hotpost_confidence_level",
    "resolve_hotpost_mode",
    "resolve_hotpost_sentiment_label",
    "resolve_hotpost_sort",
    "resolve_hotpost_time_filter",
    "search_hotpost_subreddit_posts",
    "select_hotpost_signals",
    "split_hotpost_search_queries",
]
