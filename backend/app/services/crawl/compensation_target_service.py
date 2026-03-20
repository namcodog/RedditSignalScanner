from __future__ import annotations

import hashlib
import json
import random
import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from sqlalchemy import text

from app.services.crawl.plan_contract import CrawlPlanContract


@dataclass(slots=True, frozen=True)
class CompensationTargetDeps:
    settings_factory: Callable[[], Any]
    ensure_dict: Callable[[object], dict[str, Any]]
    ensure_crawler_run_target: Callable[..., Awaitable[bool]]
    enqueue_target_outbox: Callable[..., Awaitable[bool]]
    compensation_queue: str
    backfill_posts_queue: str
    random_int: Callable[[int, int], int] = random.randint


def compute_compensation_idempotency_key(
    *,
    base_idempotency_key: str,
    reason: str,
    cursor_after: str | None,
    missing_set_hash: str | None,
    length: int = 16,
) -> str:
    raw = json.dumps(
        {
            "base": base_idempotency_key,
            "kind": "compensation",
            "reason": reason,
            "cursor_after": cursor_after,
            "missing_set_hash": missing_set_hash,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return digest[: max(8, min(length, len(digest)))]


def compute_compensation_idempotency_key_human(
    *, plan: CrawlPlanContract, reason: str, cursor_after: str | None
) -> str:
    suffix = f"|after={cursor_after}" if cursor_after else ""
    return f"{plan.target_type}:{plan.target_value}|{plan.plan_kind}|compensate|{reason}{suffix}"


async def compute_compensation_delay_seconds(
    *,
    session: Any,
    crawl_run_id: str,
    deps: CompensationTargetDeps,
) -> int:
    settings = deps.settings_factory()
    if not settings.compensation_delay_enabled:
        return 0

    base_delay = max(0, int(settings.compensation_base_delay_seconds))
    max_delay = max(0, int(settings.compensation_max_delay_seconds))
    jitter = max(0, int(settings.compensation_jitter_seconds))
    batch_size = max(1, int(settings.compensation_batch_size))
    if base_delay <= 0 and jitter <= 0:
        return 0

    try:
        result = await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM crawler_run_targets
                WHERE crawl_run_id = CAST(:rid AS uuid)
                  AND (
                    config @> '{"meta": {"is_compensation": true}}'::jsonb
                    OR config @> '{"meta": {"is_compensation": "true"}}'::jsonb
                  )
                """
            ),
            {"rid": crawl_run_id},
        )
        count = int(result.scalar() or 0)
        if count <= 0:
            rows = await session.execute(
                text(
                    """
                    SELECT config
                    FROM crawler_run_targets
                    WHERE crawl_run_id = CAST(:rid AS uuid)
                      AND config::text ILIKE '%is_compensation%'
                    """
                ),
                {"rid": crawl_run_id},
            )
            count = 0
            for row in rows.all():
                cfg = deps.ensure_dict(row[0])
                meta = deps.ensure_dict(cfg.get("meta"))
                flag = meta.get("is_compensation")
                if isinstance(flag, str):
                    flag = flag.strip().lower() == "true"
                if flag is True:
                    count += 1
    except Exception:
        return 0

    if count <= 0:
        return 0

    batch_index = max(0, (count - 1) // batch_size)
    delay = base_delay * batch_index
    if jitter > 0:
        delay += deps.random_int(0, jitter)
    if max_delay > 0:
        delay = min(delay, max_delay)
    return delay


async def enqueue_compensation_target(
    *,
    session: Any,
    crawl_run_id: str,
    subreddit: str,
    original_target_id: str,
    plan: CrawlPlanContract,
    base_idempotency_key: str,
    reason: str,
    deps: CompensationTargetDeps,
    cursor_after: str | None = None,
    missing_set_hash: str | None = None,
    countdown_seconds: int | None = None,
) -> str | None:
    meta = dict(plan.meta or {})
    meta.update(
        {
            "is_compensation": True,
            "retry_of_target_id": original_target_id,
            "compensation_reason": reason,
        }
    )
    if cursor_after:
        meta["cursor_after"] = cursor_after
    if missing_set_hash:
        meta["missing_set_hash"] = missing_set_hash

    compensation_plan = CrawlPlanContract(
        plan_kind=plan.plan_kind,
        target_type=plan.target_type,
        target_value=plan.target_value,
        reason=plan.reason,
        window=plan.window,
        limits=plan.limits,
        meta=meta,
    )

    comp_key = compute_compensation_idempotency_key(
        base_idempotency_key=base_idempotency_key,
        reason=reason,
        cursor_after=cursor_after,
        missing_set_hash=missing_set_hash,
    )
    comp_key_human = compute_compensation_idempotency_key_human(
        plan=plan,
        reason=reason,
        cursor_after=cursor_after,
    )
    comp_target_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"crawler_run_target:{crawl_run_id}:{comp_key}")
    )

    comp_dedupe_key = f"compensation:{crawl_run_id}:{comp_key}"
    was_inserted = await deps.ensure_crawler_run_target(
        session,
        community_run_id=comp_target_id,
        crawl_run_id=crawl_run_id,
        subreddit=subreddit,
        status="queued",
        plan_kind=compensation_plan.plan_kind,
        idempotency_key=comp_key,
        idempotency_key_human=comp_key_human,
        dedupe_key=comp_dedupe_key,
        config=compensation_plan.model_dump(mode="json"),
    )
    if not was_inserted:
        return None

    computed_delay = await compute_compensation_delay_seconds(
        session=session,
        crawl_run_id=crawl_run_id,
        deps=deps,
    )
    requested_delay = int(countdown_seconds or 0)
    final_delay = max(0, max(requested_delay, computed_delay))
    queue = deps.compensation_queue
    if compensation_plan.plan_kind == "backfill_posts":
        queue = deps.backfill_posts_queue
    await deps.enqueue_target_outbox(
        session,
        target_id=comp_target_id,
        queue=queue,
        countdown=final_delay if final_delay > 0 else None,
    )
    return comp_target_id


__all__ = [
    "CompensationTargetDeps",
    "compute_compensation_delay_seconds",
    "compute_compensation_idempotency_key",
    "compute_compensation_idempotency_key_human",
    "enqueue_compensation_target",
]
