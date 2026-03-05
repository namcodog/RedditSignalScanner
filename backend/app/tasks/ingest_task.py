from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from celery.utils.log import get_task_logger  # type: ignore[import-untyped]

from app.core.celery_app import celery_app
from app.db.session import SessionFactory
from app.services.community.community_cache_service import (
    mark_crawl_attempt,
    update_backfill_floor_if_lower,
    update_incremental_waterline_if_forward,
)
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
from app.services.crawl.incremental_crawler import IncrementalCrawler
from app.utils.asyncio_runner import run as run_coro
from app.utils.subreddit import subreddit_key

logger = get_task_logger(__name__)


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def _ingest_jsonl_backfill_impl(
    *,
    file_path: str,
    community: str,
    since: str,
    until: str,
    update_watermark: bool,
    crawl_run_id: str | None,
    reason: str,
    batch_size: int,
) -> dict[str, object]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"JSONL file not found: {path}")

    sub_key = subreddit_key(community)
    since_dt = _parse_dt(since)
    until_dt = _parse_dt(until)

    run_id = crawl_run_id or str(uuid.uuid4())
    plan = CrawlPlanContract(
        plan_kind="backfill_posts",
        target_type="subreddit",
        target_value=sub_key,
        reason=reason,
        window=CrawlPlanWindow(since=since_dt, until=until_dt),
        limits=CrawlPlanLimits(posts_limit=None),
        meta={"input": "jsonl", "file": str(path.name)},
    )
    idempotency_key = compute_idempotency_key(plan)
    idempotency_key_human = compute_idempotency_key_human(plan)
    community_run_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"crawler_run_target:{run_id}:{idempotency_key}")
    )

    stats: dict[str, int] = {"total": 0, "new": 0, "updated": 0, "dup": 0}
    min_seen: datetime | None = None
    max_seen: tuple[datetime, str] | None = None

    async with SessionFactory() as session:
        await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})

        # best-effort: parent + plan row
        try:
            await ensure_crawler_run(
                session,
                crawl_run_id=run_id,
                config={"mode": "ingest_jsonl", "reason": reason, "file": str(path.name)},
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

        crawler = IncrementalCrawler(
            db=session,
            reddit_client=None,
            source_track="backfill_posts",
            crawl_run_id=run_id,
            community_run_id=community_run_id,
            refresh_posts_latest_after_write=False,
        )

        batch: list[dict[str, object]] = []

        async def _flush() -> None:
            if not batch:
                return
            res = await crawler.ingest_posts_batch(sub_key, batch)
            stats["new"] += int(res.get("new", 0))
            stats["updated"] += int(res.get("updated", 0))
            stats["dup"] += int(res.get("duplicates", 0))
            batch.clear()

        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    raw = line.strip()
                    if not raw:
                        continue
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    created_utc = data.get("created_utc")
                    if created_utc is None:
                        continue
                    try:
                        created_dt = datetime.fromtimestamp(
                            float(created_utc), tz=timezone.utc
                        )
                    except Exception:
                        continue

                    if created_dt < since_dt or created_dt >= until_dt:
                        continue

                    stats["total"] += 1
                    if min_seen is None or created_dt < min_seen:
                        min_seen = created_dt
                    pid = str(data.get("id") or "")
                    if pid:
                        if max_seen is None or created_dt > max_seen[0]:
                            max_seen = (created_dt, pid)

                    batch.append(
                        {
                            "id": data.get("id"),
                            "title": data.get("title"),
                            "selftext": data.get("selftext") or data.get("body"),
                            "score": data.get("score"),
                            "num_comments": data.get("num_comments"),
                            "created_utc": data.get("created_utc"),
                            "author": data.get("author"),
                            "url": data.get("url"),
                            "permalink": data.get("permalink"),
                            "subreddit": sub_key,
                        }
                    )
                    if len(batch) >= max(1, batch_size):
                        await _flush()

            await _flush()
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

        if update_watermark and min_seen is not None and max_seen is not None:
            await update_backfill_floor_if_lower(
                sub_key,
                backfill_floor=min_seen,
                session=session,
            )
            await update_incremental_waterline_if_forward(
                sub_key,
                last_seen_post_id=max_seen[1],
                last_seen_created_at=max_seen[0],
                session=session,
            )
            await session.commit()

        metrics: dict[str, object] = {
            "status": "completed",
            "plan_kind": "backfill_posts",
            "community": sub_key,
            "window_since": since_dt.isoformat(),
            "window_until": until_dt.isoformat(),
            "update_watermark": bool(update_watermark),
            **{k: int(v) for k, v in stats.items()},
        }
        if min_seen is not None:
            metrics["min_seen_created_at"] = min_seen.isoformat()
        if max_seen is not None:
            metrics["max_seen_created_at"] = max_seen[0].isoformat()

        try:
            await complete_crawler_run_target(
                session,
                community_run_id=community_run_id,
                metrics=metrics,
            )
            await session.commit()
        except Exception:
            pass

        result: dict[str, object] = dict(metrics)
        result["crawl_run_id"] = run_id
        result["community_run_id"] = community_run_id
        result["idempotency_key"] = idempotency_key
        return result


@celery_app.task(name="tasks.crawler.ingest_jsonl_backfill")  # type: ignore[misc]
def ingest_jsonl_backfill(
    *,
    file_path: str,
    community: str,
    since: str,
    until: str,
    update_watermark: bool = True,
    crawl_run_id: str | None = None,
    reason: str = "offline_ingest",
    batch_size: int = 500,
) -> dict[str, object]:
    logger.info(
        "Ingest JSONL: %s -> %s [%s..%s] (watermark=%s, crawl_run_id=%s)",
        file_path,
        community,
        since,
        until,
        update_watermark,
        crawl_run_id,
    )
    return run_coro(
        _ingest_jsonl_backfill_impl(
            file_path=file_path,
            community=community,
            since=since,
            until=until,
            update_watermark=update_watermark,
            crawl_run_id=crawl_run_id,
            reason=reason,
            batch_size=batch_size,
        )
    )


__all__ = ["ingest_jsonl_backfill"]
