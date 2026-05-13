from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Mapping, Sequence

from sqlalchemy import text

from app.db.session import SessionFactory
from app.schemas.task import TaskSummary
from app.services.analysis.analysis_signal_support import (
    looks_like_reddit_post_id,
    truncate_target_ids,
)
from app.services.analysis.topic_profiles import TopicProfile, normalize_subreddit
from app.core.config import Settings, get_settings

_REMEDIATION_BUDGET_REDIS:Optional[ object] = None


def resolve_topic_profile_backfill_window(preferred_days:Optional[ int]) -> tuple[int, int]:
    backfill_days = 30
    backfill_slice_days = 7
    try:
        normalized_preferred_days = int(preferred_days or 0)
    except Exception:
        normalized_preferred_days = 0

    if normalized_preferred_days > 30:
        backfill_days = max(30, min(normalized_preferred_days, 365))
        backfill_slice_days = 30 if backfill_days > 90 else 7

    return backfill_days, backfill_slice_days


def get_remediation_budget_redis(settings: Settings):
    global _REMEDIATION_BUDGET_REDIS
    if _REMEDIATION_BUDGET_REDIS is None:
        from redis.asyncio import Redis

        redis_url = os.getenv("REMEDIATION_BUDGET_REDIS_URL") or settings.reddit_cache_redis_url
        _REMEDIATION_BUDGET_REDIS = Redis.from_url(redis_url, decode_responses=True)
    return _REMEDIATION_BUDGET_REDIS


async def schedule_auto_backfill_for_insufficient_samples(
    *,
    task: TaskSummary,
    topic_profile:Optional[ TopicProfile],
    open_topic_route:Optional[ Any] = None,
    keywords:Optional[ Sequence[str]] = None,
    select_top_communities_fn: Any,
) -> list[dict[str, Any]]:
    try:
        communities = (
            list(getattr(topic_profile, "allowed_communities", []) or [])
            if topic_profile is not None
            else []
        )
        if not communities and open_topic_route is not None:
            communities = [
                str(getattr(profile, "name", "")).strip()
                for profile in list(getattr(open_topic_route, "seed_profiles", ()) or ())
                if str(getattr(profile, "name", "")).strip()
            ]
        if not communities:
            fallback_profiles = select_top_communities_fn(list(keywords or []))
            communities = [
                str(getattr(profile, "name", "")).strip()
                for profile in fallback_profiles
                if str(getattr(profile, "name", "")).strip()
            ][:20]
        if not communities:
            return []

        import uuid
        from app.services.discovery.auto_backfill_service import (
            BACKFILL_POSTS_QUEUE,
            plan_auto_backfill_posts_targets,
        )
        from app.services.infrastructure.task_outbox_service import enqueue_execute_target_outbox

        def _truthy_env(name: str, default: str) -> bool:
            raw = os.getenv(name, default).strip().lower()
            return raw in {"1", "true", "yes", "y", "on"}

        def _int_env(name: str, default: int) -> int:
            raw = os.getenv(name, str(default)).strip()
            try:
                return int(raw)
            except (TypeError, ValueError):
                return int(default)

        async def _count_outbox_pending() -> int:
            try:
                async with SessionFactory() as session_outbox:
                    res = await session_outbox.execute(
                        text("SELECT COUNT(*) FROM task_outbox WHERE status = 'pending'")
                    )
                    return int(res.scalar() or 0)
            except Exception:
                return 0

        def _hour_bucket(dt: datetime) -> str:
            safe = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
            return safe.astimezone(timezone.utc).strftime("%Y%m%d%H")

        def _day_bucket(dt: datetime) -> str:
            safe = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
            return safe.astimezone(timezone.utc).strftime("%Y%m%d")

        def _membership_level() -> str:
            raw = str(getattr(task, "membership_level", None) or "free").strip().lower()
            return raw if raw in {"free", "pro", "enterprise"} else "free"

        def _hourly_user_budget(level: str) -> int:
            if level == "enterprise":
                return _int_env("REMEDIATION_USER_HOURLY_TARGET_BUDGET_ENTERPRISE", 1000)
            if level == "pro":
                return _int_env("REMEDIATION_USER_HOURLY_TARGET_BUDGET_PRO", 200)
            return _int_env("REMEDIATION_USER_HOURLY_TARGET_BUDGET_FREE", 50)

        def _daily_user_budget(level: str) -> int:
            if level == "enterprise":
                return _int_env("REMEDIATION_USER_DAILY_TARGET_BUDGET_ENTERPRISE", 5000)
            if level == "pro":
                return _int_env("REMEDIATION_USER_DAILY_TARGET_BUDGET_PRO", 1000)
            return _int_env("REMEDIATION_USER_DAILY_TARGET_BUDGET_FREE", 200)

        budget_enabled = _truthy_env("REMEDIATION_BUDGET_ENABLED", "1")
        per_task_budget = max(1, _int_env("REMEDIATION_TASK_TARGET_BUDGET", 200))
        budget_task_ttl_seconds = max(60, _int_env("REMEDIATION_TASK_BUDGET_TTL_SECONDS", 24 * 3600))
        user_budget_ttl_seconds = max(60, _int_env("REMEDIATION_USER_BUDGET_TTL_SECONDS", 2 * 3600))
        user_day_budget_ttl_seconds = max(60, _int_env("REMEDIATION_USER_DAY_BUDGET_TTL_SECONDS", 2 * 24 * 3600))

        outbox_pending_threshold = max(0, _int_env("REMEDIATION_OUTBOX_PENDING_FUSE_THRESHOLD", 5000))
        fuse_max_targets = max(0, _int_env("REMEDIATION_FUSE_MAX_TARGETS", 3))
        outbox_pending = await _count_outbox_pending()
        fuse_triggered = outbox_pending_threshold > 0 and outbox_pending >= outbox_pending_threshold

        now = datetime.now(timezone.utc)
        crawl_run_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"analysis_preflight_posts:{task.id}"))
        preferred_days = int(getattr(topic_profile, "preferred_days", 0) or 0) if topic_profile is not None else 0
        backfill_days, backfill_slice_days = resolve_topic_profile_backfill_window(preferred_days)
        try:
            from app.services.crawl.time_slicer import generate_slices

            since_dt = now - timedelta(days=max(1, int(backfill_days)))
            until_dt = now
            slices = generate_slices(
                since_dt,
                until_dt,
                slice_days=max(1, int(backfill_slice_days)),
                overlap_seconds=0,
            )
            slices_count = len(slices)
        except Exception:
            slices_count = 0

        total_posts_budget = 300
        if slices_count <= 0 or total_posts_budget <= 0:
            requested_targets_estimate = len(sorted(set(communities)))
        else:
            base = total_posts_budget // slices_count
            remainder = total_posts_budget % slices_count
            positive_slices = slices_count if base > 0 else remainder
            requested_targets_estimate = len(sorted(set(communities))) * int(positive_slices)
        max_targets_allowed = requested_targets_estimate
        budget_detail: dict[str, Any] = {
            "enabled": bool(budget_enabled),
            "requested_targets_estimate": int(requested_targets_estimate),
        }

        outbox_enqueued = 0
        outbox_deduped = 0

        if fuse_triggered:
            max_targets_allowed = min(max_targets_allowed, fuse_max_targets)
            budget_detail["circuit_breaker"] = {
                "triggered": True,
                "outbox_pending": int(outbox_pending),
                "threshold": int(outbox_pending_threshold),
                "max_targets": int(fuse_max_targets),
            }
        else:
            budget_detail["circuit_breaker"] = {
                "triggered": False,
                "outbox_pending": int(outbox_pending),
                "threshold": int(outbox_pending_threshold),
            }

        if budget_enabled:
            try:
                settings = get_settings()
                budget_redis = get_remediation_budget_redis(settings)
                task_budget_key = f"budget:remediation:task:{task.id}"
                current_task_targets = int((await budget_redis.get(task_budget_key)) or 0)
                remaining_task = max(0, per_task_budget - current_task_targets)
                budget_detail["task_budget"] = {
                    "key": task_budget_key,
                    "max": int(per_task_budget),
                    "used": int(current_task_targets),
                    "remaining": int(remaining_task),
                }
                max_targets_allowed = min(max_targets_allowed, remaining_task)

                user_id = getattr(task, "user_id", None)
                if user_id is not None:
                    level = _membership_level()
                    hourly_budget = max(0, _hourly_user_budget(level))
                    bucket = _hour_bucket(now)
                    user_budget_key = f"budget:remediation:user_hour:{user_id}:{bucket}"
                    current_user_targets = int((await budget_redis.get(user_budget_key)) or 0)
                    remaining_user = max(0, hourly_budget - current_user_targets)
                    budget_detail["user_budget_hour"] = {
                        "key": user_budget_key,
                        "level": level,
                        "max": int(hourly_budget),
                        "used": int(current_user_targets),
                        "remaining": int(remaining_user),
                    }
                    max_targets_allowed = min(max_targets_allowed, remaining_user)

                    daily_budget = max(0, _daily_user_budget(level))
                    day_bucket = _day_bucket(now)
                    user_day_key = f"budget:remediation:user_day:{user_id}:{day_bucket}"
                    current_day_targets = int((await budget_redis.get(user_day_key)) or 0)
                    remaining_day = max(0, daily_budget - current_day_targets)
                    budget_detail["user_budget_day"] = {
                        "key": user_day_key,
                        "level": level,
                        "max": int(daily_budget),
                        "used": int(current_day_targets),
                        "remaining": int(remaining_day),
                    }
                    max_targets_allowed = min(max_targets_allowed, remaining_day)
            except Exception as exc:
                budget_detail["budget_store_error"] = str(exc)

        max_targets_allowed = max(0, int(max_targets_allowed))
        budget_detail["max_targets_allowed"] = int(max_targets_allowed)

        if max_targets_allowed <= 0:
            return [{
                "type": "backfill_posts",
                "queue": BACKFILL_POSTS_QUEUE,
                "crawl_run_id": crawl_run_id,
                "targets": 0,
                "outbox_enqueued": 0,
                "outbox_deduped": 0,
                "budget_detail": budget_detail,
                "blocked_reason": "budget_or_fuse_blocked",
            }]

        async with SessionFactory() as session:
            target_ids = await plan_auto_backfill_posts_targets(
                session=session,
                crawl_run_id=crawl_run_id,
                communities=communities,
                now=now,
                days=backfill_days,
                slice_days=backfill_slice_days,
                total_posts_budget=300,
                reason="analysis_preflight_insufficient_samples",
                max_targets=max_targets_allowed,
            )
            if not target_ids:
                return [{
                    "type": "backfill_posts",
                    "queue": BACKFILL_POSTS_QUEUE,
                    "crawl_run_id": crawl_run_id,
                    "targets": 0,
                    "outbox_enqueued": 0,
                    "outbox_deduped": 0,
                    "budget_detail": budget_detail,
                    "blocked_reason": "budget_or_fuse_blocked" if max_targets_allowed <= 0 else "planner_returned_empty",
                }]
            for target_id in target_ids:
                inserted = await enqueue_execute_target_outbox(
                    session,
                    target_id=target_id,
                    queue=BACKFILL_POSTS_QUEUE,
                )
                if inserted:
                    outbox_enqueued += 1
                else:
                    outbox_deduped += 1
            await session.commit()

        if budget_enabled and outbox_enqueued > 0:
            try:
                settings = get_settings()
                budget_redis = get_remediation_budget_redis(settings)
                task_budget_key = f"budget:remediation:task:{task.id}"
                await budget_redis.incrby(task_budget_key, int(outbox_enqueued))
                await budget_redis.expire(task_budget_key, int(budget_task_ttl_seconds))
                user_id = getattr(task, "user_id", None)
                if user_id is not None:
                    bucket = _hour_bucket(now)
                    user_budget_key = f"budget:remediation:user_hour:{user_id}:{bucket}"
                    await budget_redis.incrby(user_budget_key, int(outbox_enqueued))
                    await budget_redis.expire(user_budget_key, int(user_budget_ttl_seconds))
                    day_bucket = _day_bucket(now)
                    user_day_key = f"budget:remediation:user_day:{user_id}:{day_bucket}"
                    await budget_redis.incrby(user_day_key, int(outbox_enqueued))
                    await budget_redis.expire(user_day_key, int(user_day_budget_ttl_seconds))
            except Exception:
                pass

        trimmed_ids, total_ids, truncated = truncate_target_ids(
            list(target_ids or []),
            max_items=int(os.getenv("DATA_LINEAGE_TARGET_IDS_MAX", "200") or 200),
        )
        return [{
            "type": "backfill_posts",
            "queue": BACKFILL_POSTS_QUEUE,
            "crawl_run_id": crawl_run_id,
            "targets": len(target_ids),
            "outbox_enqueued": int(outbox_enqueued),
            "outbox_deduped": int(outbox_deduped),
            "budget_detail": budget_detail,
            "target_ids": trimmed_ids,
            "target_ids_total": int(total_ids),
            "target_ids_truncated": bool(truncated),
            "communities": sorted(set(communities)),
            "window_days": backfill_days,
            "slice_days": backfill_slice_days,
        }]
    except Exception:
        return []


async def schedule_auto_backfill_for_missing_comments(
    *,
    task: TaskSummary,
    topic_profile:Optional[ TopicProfile],
    posts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    settings = get_settings()
    if not bool(getattr(settings, "incremental_comments_backfill_enabled", True)):
        return []

    raw_posts = list(posts or [])
    if not raw_posts:
        return []

    allowed: set[str] = set()
    if topic_profile is not None and getattr(topic_profile, "allowed_communities", None):
        try:
            allowed = {
                normalize_subreddit(str(x or ""))
                for x in (topic_profile.allowed_communities or [])
                if str(x or "").strip()
            }
        except Exception:
            allowed = set()

    def _post_id(post: Mapping[str, Any]) -> str:
        return str(post.get("id") or "").strip()

    def _subreddit(post: Mapping[str, Any]) -> str:
        return normalize_subreddit(str(post.get("subreddit") or ""))

    def _num_comments(post: Mapping[str, Any]) -> int:
        raw = post.get("num_comments", 0)
        try:
            return max(0, int(raw or 0))
        except (TypeError, ValueError):
            return 0

    candidates: list[dict[str, Any]] = []
    for post in raw_posts:
        pid = _post_id(post)
        if not pid or not looks_like_reddit_post_id(pid):
            continue
        sub = _subreddit(post)
        if allowed and sub not in allowed:
            continue
        num_comments = _num_comments(post)
        score = int(post.get("score") or 0)
        if num_comments <= 0 and score <= 0:
            continue
        candidates.append({"id": pid, "subreddit": sub or "unknown", "num_comments": num_comments, "score": score})
    if not candidates:
        return []

    candidates.sort(key=lambda p: (int(p.get("score") or 0), int(p.get("num_comments") or 0)), reverse=True)
    candidate_ids = [str(p["id"]) for p in candidates][:50]

    existing_counts: dict[str, int] = {}
    try:
        async with SessionFactory() as session:
            rows = await session.execute(
                text(
                    """
                    SELECT source_post_id, count(*) AS cnt
                    FROM comments
                    WHERE source = 'reddit'
                      AND source_post_id = ANY(:ids)
                    GROUP BY source_post_id
                    """
                ),
                {"ids": candidate_ids},
            )
            for row in rows.mappings().all():
                pid = str(row.get("source_post_id") or "").strip()
                if not pid:
                    continue
                try:
                    existing_counts[pid] = int(row.get("cnt") or 0)
                except (TypeError, ValueError):
                    existing_counts[pid] = 0
    except Exception:
        existing_counts = {}

    missing = [item for item in candidates if item.get("id") and existing_counts.get(str(item["id"]), 0) <= 0]
    if not missing:
        return []

    max_posts = max(1, min(int(getattr(settings, "incremental_comments_backfill_max_posts", 5) or 0), 10))
    missing = missing[:max_posts]
    comments_limit = max(1, min(int(getattr(settings, "incremental_comments_backfill_limit", 50) or 50), 200))
    depth = max(1, min(int(getattr(settings, "incremental_comments_backfill_depth", 2) or 2), 8))
    mode = str(getattr(settings, "incremental_comments_backfill_mode", "smart_shallow") or "smart_shallow").strip() or "smart_shallow"
    queue = os.getenv("COMMENTS_BACKFILL_QUEUE", "backfill_queue")

    import uuid
    from app.services.crawl.plan_contract import (
        CrawlPlanContract,
        CrawlPlanLimits,
        compute_idempotency_key,
        compute_idempotency_key_human,
    )
    from app.services.crawl.crawler_runs_service import ensure_crawler_run
    from app.services.crawl.crawler_run_targets_service import ensure_crawler_run_target
    from app.services.infrastructure.task_outbox_service import enqueue_execute_target_outbox

    crawl_run_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"analysis_preflight_comments:{task.id}"))
    now = datetime.now(timezone.utc)

    def _truthy_env(name: str, default: str) -> bool:
        raw = os.getenv(name, default).strip().lower()
        return raw in {"1", "true", "yes", "y", "on"}

    def _int_env(name: str, default: int) -> int:
        raw = os.getenv(name, str(default)).strip()
        try:
            return int(raw)
        except (TypeError, ValueError):
            return int(default)

    async def _count_outbox_pending() -> int:
        try:
            async with SessionFactory() as session_outbox:
                res = await session_outbox.execute(
                    text("SELECT COUNT(*) FROM task_outbox WHERE status = 'pending'")
                )
                return int(res.scalar() or 0)
        except Exception:
            return 0

    def _hour_bucket(dt: datetime) -> str:
        safe = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        return safe.astimezone(timezone.utc).strftime("%Y%m%d%H")

    def _day_bucket(dt: datetime) -> str:
        safe = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        return safe.astimezone(timezone.utc).strftime("%Y%m%d")

    def _membership_level() -> str:
        raw = str(getattr(task, "membership_level", None) or "free").strip().lower()
        return raw if raw in {"free", "pro", "enterprise"} else "free"

    def _hourly_user_budget(level: str) -> int:
        if level == "enterprise":
            return _int_env("REMEDIATION_USER_HOURLY_TARGET_BUDGET_ENTERPRISE", 1000)
        if level == "pro":
            return _int_env("REMEDIATION_USER_HOURLY_TARGET_BUDGET_PRO", 200)
        return _int_env("REMEDIATION_USER_HOURLY_TARGET_BUDGET_FREE", 50)

    def _daily_user_budget(level: str) -> int:
        if level == "enterprise":
            return _int_env("REMEDIATION_USER_DAILY_TARGET_BUDGET_ENTERPRISE", 5000)
        if level == "pro":
            return _int_env("REMEDIATION_USER_DAILY_TARGET_BUDGET_PRO", 1000)
        return _int_env("REMEDIATION_USER_DAILY_TARGET_BUDGET_FREE", 200)

    budget_enabled = _truthy_env("REMEDIATION_BUDGET_ENABLED", "1")
    per_task_budget = max(1, _int_env("REMEDIATION_TASK_TARGET_BUDGET", 200))
    budget_task_ttl_seconds = max(60, _int_env("REMEDIATION_TASK_BUDGET_TTL_SECONDS", 24 * 3600))
    user_budget_ttl_seconds = max(60, _int_env("REMEDIATION_USER_BUDGET_TTL_SECONDS", 2 * 3600))
    user_day_budget_ttl_seconds = max(60, _int_env("REMEDIATION_USER_DAY_BUDGET_TTL_SECONDS", 2 * 24 * 3600))

    outbox_pending_threshold = max(0, _int_env("REMEDIATION_OUTBOX_PENDING_FUSE_THRESHOLD", 5000))
    fuse_max_targets = max(0, _int_env("REMEDIATION_FUSE_MAX_TARGETS", 3))
    outbox_pending = await _count_outbox_pending()
    fuse_triggered = outbox_pending_threshold > 0 and outbox_pending >= outbox_pending_threshold

    requested_targets = len(missing)
    max_targets_allowed = requested_targets
    budget_detail: dict[str, Any] = {
        "enabled": bool(budget_enabled),
        "requested_targets": int(requested_targets),
        "circuit_breaker": {
            "triggered": bool(fuse_triggered),
            "outbox_pending": int(outbox_pending),
            "threshold": int(outbox_pending_threshold),
            "max_targets": int(fuse_max_targets),
        },
    }
    if fuse_triggered:
        max_targets_allowed = min(max_targets_allowed, fuse_max_targets)

    if budget_enabled:
        try:
            budget_redis = get_remediation_budget_redis(settings)
            task_budget_key = f"budget:remediation:task:{task.id}"
            current_task_targets = int((await budget_redis.get(task_budget_key)) or 0)
            remaining_task = max(0, per_task_budget - current_task_targets)
            budget_detail["task_budget"] = {
                "key": task_budget_key,
                "max": int(per_task_budget),
                "used": int(current_task_targets),
                "remaining": int(remaining_task),
            }
            max_targets_allowed = min(max_targets_allowed, remaining_task)

            user_id = getattr(task, "user_id", None)
            if user_id is not None:
                level = _membership_level()
                hourly_budget = max(0, _hourly_user_budget(level))
                bucket = _hour_bucket(now)
                user_budget_key = f"budget:remediation:user_hour:{user_id}:{bucket}"
                current_user_targets = int((await budget_redis.get(user_budget_key)) or 0)
                remaining_user = max(0, hourly_budget - current_user_targets)
                budget_detail["user_budget_hour"] = {
                    "key": user_budget_key,
                    "level": level,
                    "max": int(hourly_budget),
                    "used": int(current_user_targets),
                    "remaining": int(remaining_user),
                }
                max_targets_allowed = min(max_targets_allowed, remaining_user)

                daily_budget = max(0, _daily_user_budget(level))
                day_bucket = _day_bucket(now)
                user_day_key = f"budget:remediation:user_day:{user_id}:{day_bucket}"
                current_day_targets = int((await budget_redis.get(user_day_key)) or 0)
                remaining_day = max(0, daily_budget - current_day_targets)
                budget_detail["user_budget_day"] = {
                    "key": user_day_key,
                    "level": level,
                    "max": int(daily_budget),
                    "used": int(current_day_targets),
                    "remaining": int(remaining_day),
                }
                max_targets_allowed = min(max_targets_allowed, remaining_day)
        except Exception as exc:
            budget_detail["budget_store_error"] = str(exc)

    max_targets_allowed = max(0, int(max_targets_allowed))
    budget_detail["max_targets_allowed"] = int(max_targets_allowed)
    if max_targets_allowed <= 0:
        return [{
            "type": "backfill_comments",
            "queue": queue,
            "crawl_run_id": crawl_run_id,
            "targets": 0,
            "outbox_enqueued": 0,
            "outbox_deduped": 0,
            "budget_detail": budget_detail,
            "blocked_reason": "budget_or_fuse_blocked",
            "posts": [str(x.get("id") or "") for x in missing if x.get("id")][:10],
        }]

    missing = missing[:max_targets_allowed]
    target_ids: list[str] = []
    outbox_enqueued = 0
    outbox_deduped = 0
    try:
        async with SessionFactory() as session:
            await ensure_crawler_run(
                session,
                crawl_run_id=crawl_run_id,
                config={
                    "mode": "analysis_preflight_comments",
                    "task_id": str(task.id),
                    "topic_profile_id": getattr(task, "topic_profile_id", None),
                    "created_at": now.isoformat(),
                },
            )
            for item in missing:
                pid = str(item.get("id") or "").strip()
                sub = normalize_subreddit(str(item.get("subreddit") or "")) or "unknown"
                plan = CrawlPlanContract(
                    plan_kind="backfill_comments",
                    target_type="post_ids",
                    target_value=pid,
                    reason="analysis_preflight_missing_comments",
                    limits=CrawlPlanLimits(comments_limit=comments_limit),
                    meta={
                        "subreddit": sub,
                        "mode": mode,
                        "depth": depth,
                        "sort": "confidence",
                        "smart_top_limit": 30,
                        "smart_new_limit": 20,
                        "smart_reply_top_limit": 15,
                        "smart_reply_per_top": 1,
                        "smart_total_limit": comments_limit,
                        "smart_top_sort": "top",
                        "smart_new_sort": "new",
                    },
                )
                idempotency_key = compute_idempotency_key(plan)
                idempotency_key_human = compute_idempotency_key_human(plan)
                target_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"crawler_run_target:{crawl_run_id}:{idempotency_key}"))
                await ensure_crawler_run_target(
                    session,
                    community_run_id=target_id,
                    crawl_run_id=crawl_run_id,
                    subreddit=sub,
                    status="queued",
                    plan_kind=plan.plan_kind,
                    idempotency_key=idempotency_key,
                    idempotency_key_human=idempotency_key_human,
                    config=plan.model_dump(mode="json"),
                )
                inserted = await enqueue_execute_target_outbox(session, target_id=target_id, queue=queue)
                if inserted:
                    outbox_enqueued += 1
                else:
                    outbox_deduped += 1
                target_ids.append(target_id)
            await session.commit()
    except Exception:
        return []

    if budget_enabled and outbox_enqueued > 0:
        try:
            budget_redis = get_remediation_budget_redis(settings)
            task_budget_key = f"budget:remediation:task:{task.id}"
            await budget_redis.incrby(task_budget_key, int(outbox_enqueued))
            await budget_redis.expire(task_budget_key, int(budget_task_ttl_seconds))
            user_id = getattr(task, "user_id", None)
            if user_id is not None:
                bucket = _hour_bucket(now)
                user_budget_key = f"budget:remediation:user_hour:{user_id}:{bucket}"
                await budget_redis.incrby(user_budget_key, int(outbox_enqueued))
                await budget_redis.expire(user_budget_key, int(user_budget_ttl_seconds))
                day_bucket = _day_bucket(now)
                user_day_key = f"budget:remediation:user_day:{user_id}:{day_bucket}"
                await budget_redis.incrby(user_day_key, int(outbox_enqueued))
                await budget_redis.expire(user_day_key, int(user_day_budget_ttl_seconds))
        except Exception:
            pass

    return [{
        "type": "backfill_comments",
        "queue": queue,
        "crawl_run_id": crawl_run_id,
        "targets": len(target_ids),
        "outbox_enqueued": int(outbox_enqueued),
        "outbox_deduped": int(outbox_deduped),
        "budget_detail": budget_detail,
        "target_ids": truncate_target_ids(
            list(target_ids),
            max_items=int(os.getenv("DATA_LINEAGE_TARGET_IDS_MAX", "200") or 200),
        )[0],
        "posts": [str(x.get("id") or "") for x in missing if x.get("id")][:10],
    }]
