from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crawl.plan_contract import CrawlPlanContract
from app.services.infrastructure.reddit_client import RedditAPIClient
from app.utils.subreddit import subreddit_key


@dataclass(slots=True)
class BackfillCommentsWorkflowInput:
    plan: CrawlPlanContract
    session: AsyncSession
    reddit_client: RedditAPIClient
    crawl_run_id: str
    community_run_id: str


@dataclass(slots=True)
class BackfillCommentsWorkflowDeps:
    resolve_post_context: Callable[
        [AsyncSession, str, str],
        Awaitable[tuple[str, str, int | None, int | None, datetime | None]],
    ]
    count_existing_comments: Callable[[AsyncSession, str], Awaitable[int]]
    persist_comments: Callable[..., Awaitable[int]]
    classify_comments: Callable[[AsyncSession, list[str]], Awaitable[int]]
    extract_comment_entities: Callable[[AsyncSession, list[str]], Awaitable[int]]


@dataclass(slots=True)
class BackfillCommentsWorkflowResult:
    payload: dict[str, object]


async def resolve_backfill_post_context(
    session: AsyncSession,
    post_id: str,
    subreddit: str,
) -> tuple[str, str, int | None, int | None, datetime | None]:
    resolved_post_id = post_id
    resolved_subreddit = subreddit
    post_score: int | None = None
    post_num_comments: int | None = None
    post_created_at: datetime | None = None

    if resolved_post_id.isdigit():
        internal_id = int(resolved_post_id)
        row = await session.execute(
            text(
                """
                SELECT source_post_id, subreddit, score, num_comments, created_at
                FROM posts_raw
                WHERE id = :pid
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"pid": internal_id},
        )
        raw = row.first()
        if raw:
            maybe_post_id = str(raw[0] or "").strip()
            if maybe_post_id:
                resolved_post_id = maybe_post_id
            if not resolved_subreddit:
                resolved_subreddit = subreddit_key(str(raw[1] or ""))
            try:
                post_score = int(raw[2]) if raw[2] is not None else None
            except (TypeError, ValueError):
                post_score = None
            try:
                post_num_comments = int(raw[3]) if raw[3] is not None else None
            except (TypeError, ValueError):
                post_num_comments = None
            post_created_at = raw[4] if len(raw) > 4 else None

    if post_score is None or post_num_comments is None:
        row = await session.execute(
            text(
                """
                SELECT score, num_comments, created_at
                FROM posts_raw
                WHERE source_post_id = :pid
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"pid": resolved_post_id},
        )
        raw = row.first()
        if raw:
            try:
                post_score = int(raw[0]) if raw[0] is not None else None
            except (TypeError, ValueError):
                post_score = None
            try:
                post_num_comments = int(raw[1]) if raw[1] is not None else None
            except (TypeError, ValueError):
                post_num_comments = None
            post_created_at = raw[2] if len(raw) > 2 else None

    if post_created_at is not None and getattr(post_created_at, "tzinfo", None) is None:
        post_created_at = post_created_at.replace(tzinfo=timezone.utc)

    return resolved_post_id, resolved_subreddit, post_score, post_num_comments, post_created_at


async def count_existing_backfill_comments(
    session: AsyncSession,
    post_id: str,
) -> int:
    result = await session.execute(
        text(
            """
            SELECT count(*)
            FROM comments
            WHERE source = 'reddit' AND source_post_id = :pid
            """
        ),
        {"pid": post_id},
    )
    return int(result.scalar_one() or 0)


def build_smart_shallow_config(
    *,
    plan: CrawlPlanContract,
    comments_limit: int,
    post_num_comments: int | None,
    post_created_at: datetime | None,
) -> tuple[int, dict[str, Any] | None, int, str, str]:
    raw_mode = str(plan.meta.get("mode") or "").strip().lower()
    mode = raw_mode or "smart_shallow"
    default_depth = 2 if mode == "smart_shallow" else 1
    depth = max(1, min(10, int(plan.meta.get("depth") or default_depth)))
    sort = str(plan.meta.get("sort") or "confidence")

    smart_config: dict[str, Any] | None = None
    if mode == "smart_shallow":
        raw_meta = dict(plan.meta or {})
        smart_config = dict(raw_meta)
        has_custom_top = "smart_top_limit" in raw_meta
        has_custom_new = "smart_new_limit" in raw_meta
        has_custom_reply_top = "smart_reply_top_limit" in raw_meta
        smart_config.setdefault("smart_top_limit", 30)
        smart_config.setdefault("smart_new_limit", 20)
        smart_config.setdefault("smart_reply_top_limit", 15)
        smart_config.setdefault("smart_reply_per_top", 1)
        smart_config.setdefault("smart_total_limit", comments_limit)
        smart_config.setdefault("smart_top_sort", "top")
        smart_config.setdefault("smart_new_sort", "new")

        now = datetime.now(timezone.utc)
        is_recent = False
        if post_created_at is not None:
            is_recent = post_created_at >= now - timedelta(days=7)
        if not is_recent:
            if not has_custom_new:
                smart_config["smart_new_limit"] = 0
            if not has_custom_top:
                smart_config["smart_top_limit"] = 40
            if not has_custom_reply_top:
                smart_config["smart_reply_top_limit"] = 15

        if post_num_comments is not None and post_num_comments > 0:
            total_limit = int(smart_config.get("smart_total_limit") or comments_limit)
            if post_num_comments < total_limit:
                smart_config["smart_total_limit"] = post_num_comments

        comments_limit = max(
            1, min(500, int(smart_config.get("smart_total_limit") or comments_limit))
        )

    return comments_limit, smart_config, depth, sort, mode


async def execute_backfill_comments_workflow(
    *,
    workflow_input: BackfillCommentsWorkflowInput,
    deps: BackfillCommentsWorkflowDeps,
) -> BackfillCommentsWorkflowResult:
    plan = workflow_input.plan
    post_id = str(plan.target_value or "").strip()
    subreddit = subreddit_key(str(plan.meta.get("subreddit") or ""))
    if not post_id:
        raise ValueError("backfill_comments requires target_value (post_id)")

    (
        post_id,
        subreddit,
        _post_score,
        post_num_comments,
        post_created_at,
    ) = await deps.resolve_post_context(
        workflow_input.session,
        post_id,
        subreddit,
    )

    if not subreddit:
        raise ValueError("backfill_comments requires meta.subreddit")

    if post_num_comments is not None:
        if post_num_comments <= 0:
            return BackfillCommentsWorkflowResult(
                payload={
                    "plan_kind": "backfill_comments",
                    "status": "completed",
                    "processed": 0,
                    "reason": "no_comments",
                }
            )
        if post_num_comments <= 500:
            existing_count = await deps.count_existing_comments(
                workflow_input.session,
                post_id,
            )
            if existing_count >= post_num_comments:
                return BackfillCommentsWorkflowResult(
                    payload={
                        "plan_kind": "backfill_comments",
                        "status": "completed",
                        "processed": 0,
                        "reason": "already_up_to_date",
                    }
                )

    comments_limit = max(1, min(500, int(plan.limits.comments_limit or 50)))
    comments_limit, smart_config, depth, sort, mode = build_smart_shallow_config(
        plan=plan,
        comments_limit=comments_limit,
        post_num_comments=post_num_comments,
        post_created_at=post_created_at,
    )

    items = await workflow_input.reddit_client.fetch_post_comments(
        post_id,
        sort=sort,
        depth=depth,
        limit=comments_limit,
        mode=mode,
        smart_config=smart_config,
    )
    processed = await deps.persist_comments(
        workflow_input.session,
        source_post_id=post_id,
        subreddit=subreddit,
        comments=items,
        crawl_run_id=workflow_input.crawl_run_id,
        community_run_id=workflow_input.community_run_id,
        source_track="backfill_comments",
        default_business_pool="lab",
    )

    labeled = 0
    if bool(plan.meta.get("label_after_ingest")):
        ids = [str(comment.get("id")) for comment in items if comment.get("id")]
        if ids:
            labeled += await deps.classify_comments(workflow_input.session, ids)
            labeled += await deps.extract_comment_entities(workflow_input.session, ids)

    return BackfillCommentsWorkflowResult(
        payload={
            "plan_kind": "backfill_comments",
            "status": "completed",
            "processed": int(processed or 0),
            "labeled": int(labeled or 0),
        }
    )


__all__ = [
    "BackfillCommentsWorkflowDeps",
    "BackfillCommentsWorkflowInput",
    "BackfillCommentsWorkflowResult",
    "build_smart_shallow_config",
    "count_existing_backfill_comments",
    "execute_backfill_comments_workflow",
    "resolve_backfill_post_context",
]
