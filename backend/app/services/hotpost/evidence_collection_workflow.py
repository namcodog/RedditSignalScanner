from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.schemas.hotpost import Hotpost, HotpostComment, PainPoint
from app.services.hotpost.detail_builder import (
    compute_need_urgency,
    compute_rant_intensity,
)
from app.services.hotpost.keywords import HotpostLexicon
from app.services.hotpost.rules import (
    classify_pain_category,
    count_resonance,
    normalize_text,
)
from app.services.infrastructure.reddit_client import RedditPost


@dataclass(slots=True)
class HotpostEvidenceCollectionInput:
    request_query: str
    query_parts: list[str]
    keywords: list[str]
    mode: str
    time_filter: str
    sort: str
    limit: int
    requested_subreddits: list[str] | None
    suggest_subreddits_when_missing: bool
    enable_relevance_filter: bool
    max_posts_per_subreddit: int
    notes: list[str]


@dataclass(slots=True)
class HotpostEvidenceCollectionDeps:
    acquire_rate_budget: Callable[..., Awaitable[None]]
    search_subreddits: Callable[..., Awaitable[list[dict[str, Any]]]] | None
    search_subreddit_posts: Callable[..., Awaitable[tuple[list[RedditPost], int]]] | None
    search_posts: Callable[..., Awaitable[list[RedditPost]]] | None
    fetch_comments: Callable[..., Awaitable[list[dict[str, Any]]]]
    select_signals: Callable[[str, str], dict[str, list[str]]]
    sentiment_label: Callable[[str, str, dict[str, list[str]]], str]
    build_post: Callable[..., Hotpost]
    build_pain_points: Callable[[list[Hotpost], list[str]], list[PainPoint]]
    confidence_level: Callable[[int], str]
    lexicon: HotpostLexicon


@dataclass(slots=True)
class HotpostEvidenceCollectionResult:
    subreddits: list[str] | None
    api_calls: int
    raw_posts: int
    filtered_posts: int
    relevance_filtered: int
    top_posts: list[Hotpost]
    all_comments: list[HotpostComment]
    categories: list[str]
    sentiment_overview: dict[str, float]
    confidence: str
    community_distribution: dict[str, str]
    pain_points: list[PainPoint] | None
    opportunities: list[dict[str, Any]] | None
    rant_intensity: dict[str, float] | None
    need_urgency: dict[str, float] | None
    me_too_count: int
    notes: list[str]


async def collect_hotpost_evidence(
    *,
    workflow_input: HotpostEvidenceCollectionInput,
    deps: HotpostEvidenceCollectionDeps,
    queue_tracker: Any | None = None,
) -> HotpostEvidenceCollectionResult:
    notes = list(workflow_input.notes)
    subreddits = workflow_input.requested_subreddits
    api_calls = 0

    if not subreddits and workflow_input.suggest_subreddits_when_missing:
        if deps.search_subreddits is None:
            raise ValueError(
                "search_subreddits dependency is required when subreddit suggestion is enabled"
            )
        await deps.acquire_rate_budget(cost=1, queue_tracker=queue_tracker)
        suggestions = await deps.search_subreddits(
            workflow_input.query_parts[0]
            if workflow_input.query_parts
            else workflow_input.request_query,
            limit=5,
            include_nsfw=False,
        )
        subreddits = [
            item["name"].lower()
            if str(item["name"]).startswith("r/")
            else f"r/{item['name'].lower()}"
            for item in suggestions
        ]
        api_calls += 1

    posts: list[RedditPost] = []
    seen_post_ids: set[str] = set()
    if subreddits:
        if deps.search_subreddit_posts is None:
            raise ValueError(
                "search_subreddit_posts dependency is required for subreddit search"
            )
        for query_part in (workflow_input.query_parts or [workflow_input.request_query]):
            for subreddit in subreddits:
                batch, calls = await deps.search_subreddit_posts(
                    subreddit,
                    query_part,
                    sort=workflow_input.sort,
                    time_filter=workflow_input.time_filter,
                    max_posts=workflow_input.max_posts_per_subreddit,
                    queue_tracker=queue_tracker,
                )
                api_calls += calls
                for post in batch:
                    if post.id in seen_post_ids:
                        continue
                    seen_post_ids.add(post.id)
                    posts.append(post)
    else:
        if deps.search_posts is None:
            raise ValueError("search_posts dependency is required for global search")
        for query_part in (workflow_input.query_parts or [workflow_input.request_query]):
            await deps.acquire_rate_budget(cost=1, queue_tracker=queue_tracker)
            batch = await deps.search_posts(
                query_part,
                limit=min(100, workflow_input.limit),
                time_filter=workflow_input.time_filter,
                sort=workflow_input.sort,
            )
            api_calls += 1
            for post in batch:
                if post.id in seen_post_ids:
                    continue
                seen_post_ids.add(post.id)
                posts.append(post)

    filtered: list[Hotpost] = []
    categories: list[str] = []
    sentiment_labels: list[str] = []
    signal_groups_list: list[dict[str, list[str]]] = []
    relevance_filtered = 0
    relevance_terms = [
        term.lower() for term in workflow_input.keywords if term and term.isascii()
    ]
    for post in posts:
        text = normalize_text(f"{post.title} {post.selftext}")
        signals = deps.select_signals(workflow_input.mode, text)
        if workflow_input.mode in {"rant", "opportunity"} and not any(signals.values()):
            continue
        if (
            workflow_input.mode == "opportunity"
            and workflow_input.enable_relevance_filter
            and relevance_terms
            and not any(term in text for term in relevance_terms)
        ):
            relevance_filtered += 1
            continue
        category = classify_pain_category(text, deps.lexicon)
        categories.append(category)
        sentiment_labels.append(
            deps.sentiment_label(workflow_input.mode, text, signals)
        )
        signal_groups_list.append(signals)
        filtered.append(deps.build_post(post, rank=len(filtered) + 1, signals=signals))
        if len(filtered) >= workflow_input.limit:
            break

    top_posts = filtered[: workflow_input.limit]
    if relevance_filtered:
        notes.append(f"已过滤 {relevance_filtered} 条低相关帖子")

    all_comments: list[HotpostComment] = []
    for post in top_posts[:30]:
        comments = await deps.fetch_comments(post.id, queue_tracker=queue_tracker)
        hotpost_comments: list[HotpostComment] = []
        for comment in comments:
            hot_comment = HotpostComment(
                comment_fullname=comment.get("name") or comment.get("fullname"),
                author=comment.get("author"),
                body=comment.get("body"),
                score=int(comment.get("score") or 0),
                permalink=comment.get("permalink"),
            )
            hotpost_comments.append(hot_comment)
            all_comments.append(hot_comment)
        post.top_comments = hotpost_comments

    evidence_count = len(top_posts)
    community_counts = Counter(post.subreddit for post in top_posts)
    community_distribution = {
        subreddit: f"{count / evidence_count * 100:.0f}" + "%"
        if evidence_count
        else "0%"
        for subreddit, count in community_counts.most_common(5)
    }
    sentiment_counts = Counter(sentiment_labels)
    sentiment_overview = {
        "positive": sentiment_counts.get("positive", 0) / evidence_count
        if evidence_count
        else 0.0,
        "neutral": sentiment_counts.get("neutral", 0) / evidence_count
        if evidence_count
        else 0.0,
        "negative": sentiment_counts.get("negative", 0) / evidence_count
        if evidence_count
        else 0.0,
    }
    confidence = deps.confidence_level(evidence_count)
    rant_intensity = (
        compute_rant_intensity(signal_groups_list)
        if workflow_input.mode == "rant"
        else None
    )
    need_urgency = (
        compute_need_urgency(signal_groups_list)
        if workflow_input.mode == "opportunity"
        else None
    )
    pain_points = (
        deps.build_pain_points(top_posts, categories)
        if workflow_input.mode == "rant"
        else None
    )
    me_too_count = count_resonance(
        [comment.model_dump() for comment in all_comments],
        deps.lexicon,
    )
    opportunities = None
    if workflow_input.mode == "opportunity":
        opportunities = [
            {
                "summary": "用户在讨论中表达了需求缺口",
                "me_too_count": me_too_count,
            }
        ]

    return HotpostEvidenceCollectionResult(
        subreddits=subreddits,
        api_calls=api_calls,
        raw_posts=len(posts),
        filtered_posts=len(filtered),
        relevance_filtered=relevance_filtered,
        top_posts=top_posts,
        all_comments=all_comments,
        categories=categories,
        sentiment_overview=sentiment_overview,
        confidence=confidence,
        community_distribution=community_distribution,
        pain_points=pain_points,
        opportunities=opportunities,
        rant_intensity=rant_intensity,
        need_urgency=need_urgency,
        me_too_count=me_too_count,
        notes=notes,
    )


__all__ = [
    "HotpostEvidenceCollectionDeps",
    "HotpostEvidenceCollectionInput",
    "HotpostEvidenceCollectionResult",
    "collect_hotpost_evidence",
]
