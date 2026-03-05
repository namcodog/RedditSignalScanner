from __future__ import annotations

import uuid
from datetime import datetime, timezone

from celery.utils.log import get_task_logger  # type: ignore[import-untyped]

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.community.community_cache_service import mark_crawl_attempt
from app.services.crawl.execute_plan import execute_crawl_plan
from app.services.crawl.plan_contract import (
    CrawlPlanContract,
    CrawlPlanLimits,
    CrawlPlanWindow,
    compute_idempotency_key,
    compute_idempotency_key_human,
)
from app.services.crawl.crawler_run_targets_service import (
    complete_crawler_run_target,
    ensure_crawler_run_target,
    fail_crawler_run_target,
)
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.infrastructure.reddit_client import RedditAPIClient
from app.utils.asyncio_runner import run as run_coro
from app.utils.subreddit import subreddit_key

logger = get_task_logger(__name__)


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def _backfill_posts_window_impl(
    *,
    subreddit: str,
    since: str,
    until: str,
    posts_limit: int,
    crawl_run_id: str | None,
    reason: str,
) -> dict[str, object]:
    settings = get_settings()
    sub_key = subreddit_key(subreddit)
    since_dt = _parse_dt(since)
    until_dt = _parse_dt(until)

    run_id = crawl_run_id or str(uuid.uuid4())
    plan = CrawlPlanContract(
        plan_kind="backfill_posts",
        target_type="subreddit",
        target_value=sub_key,
        reason=reason,
        window=CrawlPlanWindow(since=since_dt, until=until_dt),
        limits=CrawlPlanLimits(posts_limit=max(1, int(posts_limit))),
        meta={"sort": "new"},
    )
    idempotency_key = compute_idempotency_key(plan)
    idempotency_key_human = compute_idempotency_key_human(plan)
    community_run_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"crawler_run_target:{run_id}:{idempotency_key}",
        )
    )

    async with RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=settings.reddit_max_concurrency,
    ) as reddit:
        async with SessionFactory() as session:
            await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})

            # best-effort: parent + plan row
            try:
                await ensure_crawler_run(
                    session,
                    crawl_run_id=run_id,
                    config={"mode": "backfill_posts", "reason": reason},
                )
                await ensure_crawler_run_target(
                    session,
                    community_run_id=community_run_id,
                    crawl_run_id=run_id,
                    subreddit=sub_key,
                    plan_kind=plan.plan_kind,
                    idempotency_key=idempotency_key,
                    idempotency_key_human=idempotency_key_human,
                    config=plan.model_dump(mode="json"),
                )
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass

            try:
                outcome = await execute_crawl_plan(
                    plan=plan,
                    session=session,
                    reddit_client=reddit,
                    crawl_run_id=run_id,
                    community_run_id=community_run_id,
                )
            except Exception as exc:
                await mark_crawl_attempt(sub_key, session=session)
                try:
                    await fail_crawler_run_target(
                        session,
                        community_run_id=community_run_id,
                        error_message_short=str(exc)[:400],
                    )
                    await session.commit()
                except Exception:
                    pass
                raise

            try:
                await complete_crawler_run_target(
                    session,
                    community_run_id=community_run_id,
                    metrics=outcome,
                )
                await session.commit()
            except Exception:
                pass

            result: dict[str, object] = dict(outcome)
            result["crawl_run_id"] = run_id
            result["community_run_id"] = community_run_id
            result["idempotency_key"] = idempotency_key
            return result


@celery_app.task(name="tasks.crawler.backfill_posts_window")  # type: ignore[misc]
def backfill_posts_window(
    *,
    subreddit: str,
    since: str,
    until: str,
    posts_limit: int = 1000,
    crawl_run_id: str | None = None,
    reason: str = "cold_start",
) -> dict[str, object]:
    logger.info(
        "Backfill posts window: %s [%s..%s] limit=%s (crawl_run_id=%s)",
        subreddit,
        since,
        until,
        posts_limit,
        crawl_run_id,
    )
    return run_coro(
        _backfill_posts_window_impl(
            subreddit=subreddit,
            since=since,
            until=until,
            posts_limit=posts_limit,
            crawl_run_id=crawl_run_id,
            reason=reason,
        )
    )


__all__ = ["backfill_posts_window"]
