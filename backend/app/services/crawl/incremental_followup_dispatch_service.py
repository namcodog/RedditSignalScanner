from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from app.services.infrastructure.reddit_client import RedditPost
from app.utils.subreddit import subreddit_key

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class IncrementalScoreRefreshInput:
    new_count: int


@dataclass(slots=True)
class CommentBackfillDispatchInput:
    community_name: str
    posts: list[RedditPost]
    enabled: bool
    max_posts: int
    mode: str
    limit: int
    depth: int


@dataclass(slots=True)
class IncrementalFollowupDispatchDeps:
    send_task: Callable[..., object]


async def dispatch_incremental_score_refresh(
    refresh_input: IncrementalScoreRefreshInput,
    deps: IncrementalFollowupDispatchDeps,
) -> None:
    try:
        deps.send_task(
            "tasks.analysis.score_new_posts_v1",
            kwargs={"limit": max(200, refresh_input.new_count + 50)},
        )
    except Exception:
        logger.exception("Failed to dispatch score_new_posts_v1 after crawl")


def enqueue_comment_backfill(
    dispatch_input: CommentBackfillDispatchInput,
    deps: IncrementalFollowupDispatchDeps,
) -> None:
    if not dispatch_input.enabled or not dispatch_input.posts:
        return
    if dispatch_input.max_posts <= 0:
        return

    candidates = [post for post in dispatch_input.posts if (post.num_comments or 0) > 0]
    if not candidates:
        return

    candidates.sort(key=lambda post: post.num_comments or 0, reverse=True)
    targets = candidates[: dispatch_input.max_posts]
    try:
        for post in targets:
            deps.send_task(
                "comments.fetch_and_ingest",
                kwargs={
                    "source_post_id": post.id,
                    "subreddit": subreddit_key(dispatch_input.community_name),
                    "mode": dispatch_input.mode,
                    "limit": dispatch_input.limit,
                    "depth": dispatch_input.depth,
                },
            )
    except Exception:
        logger.exception("Failed to dispatch comments.fetch_and_ingest")


def schedule_posts_latest_refresh(
    deps: IncrementalFollowupDispatchDeps,
) -> None:
    try:
        deps.send_task("tasks.maintenance.refresh_posts_latest")
    except Exception:  # pragma: no cover - 调度失败时仅记录日志
        logger.exception("Failed to schedule posts_latest refresh task")


__all__ = [
    "CommentBackfillDispatchInput",
    "IncrementalFollowupDispatchDeps",
    "IncrementalScoreRefreshInput",
    "dispatch_incremental_score_refresh",
    "enqueue_comment_backfill",
    "schedule_posts_latest_refresh",
]
