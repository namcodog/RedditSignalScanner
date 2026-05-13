from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from app.utils.subreddit import subreddit_key

__all__ = [
    "backfill_comments_min",
    "backfill_done_months",
    "backfill_posts_min",
    "build_global_rate_limiter",
    "count_comments_since",
    "count_posts_since",
    "ensure_dict",
    "finalize_backfill_status",
    "load_backfill_floor",
    "load_community_blacklist_status",
    "needs_community_lock",
    "parse_iso_datetime",
    "parse_uuid",
    "release_community_lock",
    "try_acquire_community_lock",
]


def parse_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except Exception as exc:
        raise ValueError("target_id must be a UUID string") from exc


def ensure_dict(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
            return loaded if isinstance(loaded, dict) else {}
        except Exception:
            return {}
    return {}


async def load_community_blacklist_status(
    *, session: Any, subreddit: str
) -> bool | None:
    return await session.scalar(
        text(
            """
            WITH truth_decisions AS (
                SELECT g.decision
                FROM community_registry r
                JOIN community_domain_membership m
                  ON m.community_id = r.id
                 AND m.is_current = TRUE
                JOIN community_governance_decision g
                  ON g.membership_id = m.id
                 AND g.is_current = TRUE
                WHERE r.platform = 'reddit'
                  AND lower(r.community_name) = lower(:name)
            ),
            truth_status AS (
                SELECT
                    COUNT(*) AS decision_count,
                    CASE
                        WHEN BOOL_OR(decision = 'blocked') THEN TRUE
                        WHEN BOOL_OR(decision = 'approved') THEN FALSE
                        ELSE NULL
                    END AS is_blacklisted
                FROM truth_decisions
            ),
            pool_status AS (
                SELECT is_blacklisted
                FROM community_pool
                WHERE lower(name) = lower(:name)
                LIMIT 1
            )
            SELECT
                CASE
                    WHEN truth_status.decision_count > 0
                    THEN truth_status.is_blacklisted
                    ELSE pool_status.is_blacklisted
                END
            FROM truth_status
            LEFT JOIN pool_status ON TRUE
            """
        ),
        {"name": subreddit},
    )


def build_global_rate_limiter(
    *,
    settings: Any,
    plan_kind: str,
    crawler_global_bucket_enabled: bool,
) -> Any | None:
    if not crawler_global_bucket_enabled:
        return None

    try:
        import redis.asyncio as redis  # type: ignore
    except Exception:
        return None

    try:
        from app.services.infrastructure import global_rate_limiter
    except Exception:
        return None

    try:
        share_raw = os.getenv("CRAWLER_PATROL_BUCKET_SHARE", "0.4")
        patrol_share = float(share_raw)
    except Exception:
        patrol_share = 0.4
    patrol_share = max(0.05, min(0.95, patrol_share))

    total_limit = max(1, int(getattr(settings, "reddit_rate_limit", 1) or 1))
    window_seconds = int(
        float(getattr(settings, "reddit_rate_limit_window_seconds", 60.0) or 60.0)
    )
    window_seconds = max(1, window_seconds)

    patrol_limit = max(1, int(round(total_limit * patrol_share)))
    bulk_limit = max(1, total_limit - patrol_limit)
    is_patrol = str(plan_kind) == "patrol"
    bucket_name = "patrol" if is_patrol else "bulk"
    bucket_limit = patrol_limit if is_patrol else bulk_limit

    try:
        client_id = str(getattr(settings, "reddit_client_id", "") or "default")
        rclient = redis.Redis.from_url(getattr(settings, "reddit_cache_redis_url"))
        return global_rate_limiter.GlobalRateLimiter(
            rclient,
            limit=bucket_limit,
            window_seconds=window_seconds,
            namespace=f"reddit_api:qpm:{bucket_name}",
            client_id=client_id,
        )
    except Exception:
        return None


def needs_community_lock(plan_kind: str, *, locked_plan_kinds: set[str]) -> bool:
    return str(plan_kind) in locked_plan_kinds


async def try_acquire_community_lock(*, session: Any, community_name: str) -> bool:
    lock_key = subreddit_key(community_name)
    result = await session.execute(
        text("SELECT pg_try_advisory_lock(hashtext(:key))"),
        {"key": lock_key},
    )
    return bool(result.scalar() or False)


async def release_community_lock(*, session: Any, community_name: str) -> None:
    lock_key = subreddit_key(community_name)
    await session.execute(
        text("SELECT pg_advisory_unlock(hashtext(:key))"),
        {"key": lock_key},
    )


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def backfill_done_months() -> int:
    return max(1, int(os.getenv("BACKFILL_DONE_MONTHS", "12")))


def backfill_posts_min() -> int:
    return max(1, int(os.getenv("BACKFILL_DONE_POSTS_MIN", "1000")))


def backfill_comments_min() -> int:
    return max(1, int(os.getenv("BACKFILL_DONE_COMMENTS_MIN", "20000")))


async def count_posts_since(*, session: Any, subreddit: str, since: datetime) -> int:
    result = await session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM posts_raw
            WHERE subreddit = :subreddit
              AND created_at >= :since
            """
        ),
        {"subreddit": subreddit_key(subreddit), "since": since},
    )
    return int(result.scalar() or 0)


async def count_comments_since(*, session: Any, subreddit: str, since: datetime) -> int:
    result = await session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM comments
            WHERE subreddit = :subreddit
              AND created_utc >= :since
            """
        ),
        {"subreddit": subreddit_key(subreddit), "since": since},
    )
    return int(result.scalar() or 0)


async def load_backfill_floor(*, session: Any, subreddit: str) -> datetime | None:
    result = await session.execute(
        text(
            """
            WITH runtime_status AS (
                SELECT s.backfill_floor
                FROM community_registry r
                JOIN community_runtime_state s
                  ON s.community_id = r.id
                WHERE r.platform = 'reddit'
                  AND lower(r.community_name) = lower(:name)
                LIMIT 1
            ),
            cache_status AS (
                SELECT backfill_floor
                FROM community_cache
                WHERE lower(community_name) = lower(:key)
                LIMIT 1
            )
            SELECT COALESCE(
                (SELECT backfill_floor FROM runtime_status),
                (SELECT backfill_floor FROM cache_status)
            )
            """
        ),
        {"name": subreddit, "key": subreddit_key(subreddit)},
    )
    floor = result.scalar_one_or_none()
    if floor is not None and getattr(floor, "tzinfo", None) is None:
        floor = floor.replace(tzinfo=timezone.utc)
    return floor


async def finalize_backfill_status(
    *,
    session: Any,
    subreddit: str,
    plan: Any,
    outcome: dict[str, object],
    parse_iso_datetime_func: Any,
    backfill_done_months_func: Any,
    backfill_posts_min_func: Any,
    backfill_comments_min_func: Any,
    load_backfill_floor_func: Any,
    count_posts_since_func: Any,
    count_comments_since_func: Any,
    update_backfill_status_func: Any,
) -> None:
    now = datetime.now(timezone.utc)
    window_since = plan.window.since if plan.window is not None else None
    min_seen = parse_iso_datetime_func(str(outcome.get("min_seen_created_at") or ""))
    cursor_after = str(outcome.get("cursor_after") or "") or None
    reason = str(outcome.get("reason") or "")
    total_fetched = int(outcome.get("total_fetched") or 0)
    posts_limit = int(plan.limits.posts_limit or 0)
    hit_posts_limit = bool(outcome.get("hit_posts_limit"))
    if posts_limit > 0 and total_fetched >= posts_limit:
        hit_posts_limit = True

    backfill_floor = await load_backfill_floor_func(
        session=session, subreddit=subreddit
    )
    coverage_months = max(0, (now - backfill_floor).days // 30) if backfill_floor else 0

    since_window = now - timedelta(days=backfill_done_months_func() * 30)
    sample_posts = await count_posts_since_func(
        session=session, subreddit=subreddit, since=since_window
    )
    sample_comments = await count_comments_since_func(
        session=session, subreddit=subreddit, since=since_window
    )

    backfill_capped = False
    if reason == "cursor_remaining" or hit_posts_limit:
        backfill_capped = True
    elif cursor_after:
        backfill_capped = False
    elif min_seen is not None and window_since is not None and min_seen > window_since:
        backfill_capped = True

    status = "NEEDS"
    done_floor = now - timedelta(days=backfill_done_months_func() * 30)
    if backfill_floor is not None and backfill_floor <= done_floor:
        status = "DONE_12M"
    elif (
        backfill_capped
        and sample_posts >= backfill_posts_min_func()
        and sample_comments >= backfill_comments_min_func()
    ):
        status = "DONE_CAPPED"
    elif backfill_capped:
        status = "ERROR"

    await update_backfill_status_func(
        subreddit_key(subreddit),
        status=status,
        coverage_months=int(coverage_months),
        sample_posts=sample_posts,
        sample_comments=sample_comments,
        backfill_capped=backfill_capped,
        cursor_after=cursor_after,
        cursor_created_at=min_seen,
        session=session,
    )
