from __future__ import annotations

import os
from typing import Any, Iterable, Mapping

from celery.utils.log import get_task_logger  # type: ignore[import-untyped]

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.crawl.comments_ingest import persist_comments
from app.services.crawl.comments_task_runtime import (
    build_comments_task_runtime_deps,
    run_backfill_full_comments,
    run_backfill_high_value_comments,
    run_backfill_recent_full_daily,
    run_capture_snapshot_daily,
    run_fetch_and_ingest_post_comments,
    run_ingest_post_comments,
    run_label_comments_task,
    run_label_posts_recent_task,
)
from app.services.crawl.crawler_run_targets_service import ensure_crawler_run_target
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.infrastructure.moderation_metrics import (
    compute_removal_ratio_by_subreddit,
    to_rules_friendliness_score,
)
from app.services.infrastructure.reddit_client import RedditAPIClient
from app.services.infrastructure.subreddit_snapshot import persist_subreddit_snapshot
from app.services.infrastructure.task_outbox_service import enqueue_execute_target_outbox
from app.services.labeling.labeling_posts import label_posts_recent
from app.services.labeling.labeling_service import (
    classify_and_label_comments,
    extract_and_label_entities_for_comments,
)
from app.utils.asyncio_runner import run as run_coro

logger = get_task_logger(__name__)
COMMENTS_BACKFILL_QUEUE = os.getenv("COMMENTS_BACKFILL_QUEUE", "backfill_queue")


def _runtime_deps() -> Any:
    return build_comments_task_runtime_deps(
        session_factory=SessionFactory,
        persist_comments=persist_comments,
        ensure_crawler_run=ensure_crawler_run,
        ensure_crawler_run_target=ensure_crawler_run_target,
        enqueue_execute_target_outbox=enqueue_execute_target_outbox,
        reddit_client_cls=RedditAPIClient,
        classify_and_label_comments=classify_and_label_comments,
        extract_and_label_entities_for_comments=extract_and_label_entities_for_comments,
        persist_subreddit_snapshot=persist_subreddit_snapshot,
        label_posts_recent=label_posts_recent,
        compute_removal_ratio_by_subreddit=compute_removal_ratio_by_subreddit,
        to_rules_friendliness_score=to_rules_friendliness_score,
    )


@celery_app.task(name="comments.ingest_post_comments")
def ingest_post_comments(
    *,
    source_post_id: str,
    subreddit: str,
    comments: Iterable[Mapping[str, Any]],
    source: str = "reddit",
) -> dict[str, int | str]:
    return run_coro(
        run_ingest_post_comments(
            deps=_runtime_deps(),
            source_post_id=source_post_id,
            subreddit=subreddit,
            comments=comments,
            source=source,
        )
    )


@celery_app.task(name="comments.fetch_and_ingest")
def fetch_and_ingest_post_comments(
    *,
    source_post_id: str,
    subreddit: str,
    mode: str = "smart_shallow",
    limit: int = 50,
    depth: int = 2,
) -> dict[str, int | str]:
    return run_coro(
        run_fetch_and_ingest_post_comments(
            deps=_runtime_deps(),
            queue=COMMENTS_BACKFILL_QUEUE,
            source_post_id=source_post_id,
            subreddit=subreddit,
            mode=mode,
            limit=limit,
            depth=depth,
        )
    )


@celery_app.task(name="comments.label_comments")
def label_comments_task(*, reddit_comment_ids: list[str]) -> dict[str, int | str]:
    return run_coro(
        run_label_comments_task(
            deps=_runtime_deps(),
            reddit_comment_ids=reddit_comment_ids,
        )
    )


@celery_app.task(name="comments.backfill_full")
def backfill_full_comments(
    *,
    source_post_ids: list[str],
    subreddit: str,
    limit: int = 500,
) -> dict[str, int | str]:
    return run_coro(
        run_backfill_full_comments(
            deps=_runtime_deps(),
            queue=COMMENTS_BACKFILL_QUEUE,
            source_post_ids=source_post_ids,
            subreddit=subreddit,
            limit=limit,
        )
    )


@celery_app.task(name="comments.backfill_recent_full_daily")
def backfill_recent_full_daily() -> dict[str, int | str]:
    return run_coro(
        run_backfill_recent_full_daily(
            deps=_runtime_deps(),
            settings=get_settings(),
            queue=COMMENTS_BACKFILL_QUEUE,
            subreddits_raw=os.getenv("COMMENTS_BACKFILL_SUBS", "").strip(),
            lookback_days=int(os.getenv("COMMENTS_BACKFILL_DAYS", "7")),
            per_sub_limit=int(os.getenv("COMMENTS_BACKFILL_POST_LIMIT", "20")),
        )
    )


@celery_app.task(name="subreddit.capture_snapshot_daily")
def capture_snapshot_daily() -> dict[str, int | str]:
    return run_coro(
        run_capture_snapshot_daily(
            deps=_runtime_deps(),
            settings=get_settings(),
            subreddits_raw=os.getenv("COMMENTS_BACKFILL_SUBS", "").strip(),
        )
    )


@celery_app.task(name="posts.label_recent")
def label_posts_recent_task() -> dict[str, int | str]:
    return run_coro(
        run_label_posts_recent_task(
            deps=_runtime_deps(),
            since_days=int(os.getenv("POSTS_LABEL_DAYS", "7")),
            limit=int(os.getenv("POSTS_LABEL_LIMIT", "500")),
        )
    )


@celery_app.task(name="comments.backfill_high_value_full")
def backfill_high_value_comments() -> dict[str, int | str]:
    return run_coro(
        run_backfill_high_value_comments(
            deps=_runtime_deps(),
            settings=get_settings(),
            per_sub_limit=int(os.getenv("HIGH_VALUE_COMMENTS_POST_LIMIT", "50")),
            lookback_days=int(os.getenv("HIGH_VALUE_COMMENTS_LOOKBACK_DAYS", "30")),
            logger=logger,
        )
    )
