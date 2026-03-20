from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Sequence

from app.services.infrastructure.reddit_client import RedditPost


@dataclass(slots=True)
class SingleCrawlWorkflowInput:
    community_name: str
    post_limit: int
    time_filter: str
    sort: str
    start_time: datetime
    community_cache_ttl_seconds: int
    hot_cache_ttl_hours: int | None
    comments_preview_enabled: bool
    comments_topn_limit: int


@dataclass(slots=True)
class SingleCrawlWorkflowDeps:
    normalize_subreddit_name: Callable[[str], str]
    fetch_comprehensive_posts: Callable[[str, str, int], Awaitable[Sequence[RedditPost]]]
    fetch_subreddit_posts: Callable[[str, int, str, str], Awaitable[Sequence[RedditPost] | tuple[Sequence[RedditPost], Any]]]
    is_rate_limit_error: Callable[[Exception], bool]
    set_cached_posts: Callable[[str, Sequence[RedditPost], int | None], Awaitable[None]]
    upsert_community_cache: Callable[[str, int, int], Awaitable[None]]
    fetch_subreddit_about: Callable[[str], Awaitable[dict[str, Any]]]
    fetch_subreddit_rules: Callable[[str], Awaitable[str]]
    session_factory: Callable[[], Any]
    persist_subreddit_snapshot: Callable[..., Awaitable[None]]
    fetch_post_comments: Callable[..., Awaitable[Sequence[Any]]]
    persist_comments: Callable[..., Awaitable[None]]
    rollback_with_warning: Callable[[Any, str], Awaitable[None]]
    log_debug: Callable[[str, Exception], None]


@dataclass(slots=True)
class SingleCrawlWorkflowResult:
    payload: dict[str, Any]


def _coerce_posts(
    payload: Sequence[RedditPost] | tuple[Sequence[RedditPost], Any],
) -> list[RedditPost]:
    if isinstance(payload, tuple):
        return list(payload[0])
    return list(payload)


async def run_single_crawl_workflow(
    *,
    workflow_input: SingleCrawlWorkflowInput,
    deps: SingleCrawlWorkflowDeps,
) -> SingleCrawlWorkflowResult:
    community_name = workflow_input.community_name
    api_subreddit = deps.normalize_subreddit_name(community_name)
    rate_limited = False
    effective_post_limit = workflow_input.post_limit

    try:
        if workflow_input.post_limit > 100:
            posts = list(
                await deps.fetch_comprehensive_posts(
                    api_subreddit,
                    workflow_input.time_filter,
                    workflow_input.post_limit,
                )
            )
        else:
            posts = _coerce_posts(
                await deps.fetch_subreddit_posts(
                    api_subreddit,
                    workflow_input.post_limit,
                    workflow_input.time_filter,
                    workflow_input.sort,
                )
            )
    except Exception as exc:
        if not deps.is_rate_limit_error(exc):
            raise
        rate_limited = True
        effective_post_limit = min(80, max(20, int(workflow_input.post_limit / 2) or 20))
        posts = _coerce_posts(
            await deps.fetch_subreddit_posts(
                api_subreddit,
                effective_post_limit,
                workflow_input.time_filter,
                workflow_input.sort,
            )
        )

    ttl_seconds = None
    if workflow_input.hot_cache_ttl_hours is not None:
        ttl_seconds = max(60, int(workflow_input.hot_cache_ttl_hours) * 3600)

    await deps.set_cached_posts(community_name, posts, ttl_seconds)
    await deps.upsert_community_cache(
        community_name,
        len(posts),
        workflow_input.community_cache_ttl_seconds,
    )

    duration = (datetime.now(timezone.utc) - workflow_input.start_time).total_seconds()

    try:
        about = await deps.fetch_subreddit_about(api_subreddit)
        rules_text = await deps.fetch_subreddit_rules(api_subreddit)
        async with deps.session_factory() as db:
            await deps.persist_subreddit_snapshot(
                db,
                subreddit=api_subreddit,
                subscribers=about.get("subscribers"),
                active_user_count=about.get("active_user_count"),
                rules_text=rules_text,
                over18=about.get("over18"),
            )
            await db.commit()
    except Exception as exc:
        deps.log_debug(f"subreddit snapshot failed for {api_subreddit}", exc)

    if workflow_input.comments_preview_enabled and posts:
        try:
            comment_crawl_run_id = str(uuid.uuid4())
            async with deps.session_factory() as db:
                for post in posts:
                    try:
                        items = await deps.fetch_post_comments(
                            post.id,
                            sort="confidence",
                            depth=1,
                            limit=min(workflow_input.comments_topn_limit, 20),
                            mode="topn",
                        )
                        if not items:
                            continue
                        await deps.persist_comments(
                            db,
                            source_post_id=post.id,
                            subreddit=api_subreddit,
                            comments=items,
                            source_track="incremental_preview",
                            crawl_run_id=comment_crawl_run_id,
                        )
                        await db.commit()
                    except Exception as exc:
                        await deps.rollback_with_warning(db, "comment_sync")
                        deps.log_debug(f"Comment sync failed for {post.id}", exc)
        except Exception as exc:
            deps.log_debug("Comment sync skipped", exc)

    return SingleCrawlWorkflowResult(
        payload={
            "community": community_name,
            "posts_count": len(posts),
            "status": "success",
            "duration_seconds": duration,
            "rate_limited": rate_limited,
            "effective_post_limit": effective_post_limit,
        }
    )


__all__ = [
    "SingleCrawlWorkflowDeps",
    "SingleCrawlWorkflowInput",
    "SingleCrawlWorkflowResult",
    "run_single_crawl_workflow",
]
