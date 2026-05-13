from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any, Iterable, Mapping

from app.core.config import Settings
from sqlalchemy import text

from app.services.crawl.comments_task_support import (
    DEFAULT_HIGH_VALUE_SUBREDDITS,
    build_backfill_comments_plan,
    build_reddit_client_kwargs,
    enqueue_backfill_comments_target,
    normalize_configured_subreddits,
    select_time_filter,
)


def build_comments_task_runtime_deps(
    *,
    session_factory: Any,
    persist_comments: Any,
    ensure_crawler_run: Any,
    ensure_crawler_run_target: Any,
    enqueue_execute_target_outbox: Any,
    reddit_client_cls: Any,
    classify_and_label_comments: Any,
    extract_and_label_entities_for_comments: Any,
    persist_subreddit_snapshot: Any,
    label_posts_recent: Any,
    compute_removal_ratio_by_subreddit: Any,
    to_rules_friendliness_score: Any,
) -> SimpleNamespace:
    return SimpleNamespace(
        session_factory=session_factory,
        persist_comments=persist_comments,
        ensure_crawler_run=ensure_crawler_run,
        ensure_crawler_run_target=ensure_crawler_run_target,
        enqueue_execute_target_outbox=enqueue_execute_target_outbox,
        reddit_client_cls=reddit_client_cls,
        classify_and_label_comments=classify_and_label_comments,
        extract_and_label_entities_for_comments=extract_and_label_entities_for_comments,
        persist_subreddit_snapshot=persist_subreddit_snapshot,
        label_posts_recent=label_posts_recent,
        compute_removal_ratio_by_subreddit=compute_removal_ratio_by_subreddit,
        to_rules_friendliness_score=to_rules_friendliness_score,
        build_backfill_comments_plan=build_backfill_comments_plan,
        enqueue_backfill_comments_target=enqueue_backfill_comments_target,
        normalize_configured_subreddits=normalize_configured_subreddits,
        select_time_filter=select_time_filter,
        build_reddit_client_kwargs=build_reddit_client_kwargs,
        high_value_subreddits=DEFAULT_HIGH_VALUE_SUBREDDITS,
    )


async def run_ingest_post_comments(
    *,
    deps: Any,
    source_post_id: str,
    subreddit: str,
    comments: Iterable[Mapping[str, Any]],
    source: str,
) -> dict[str, int | str]:
    items = list(comments)
    crawl_run_id = str(uuid.uuid4())
    async with deps.session_factory() as session:
        processed = await deps.persist_comments(
            session,
            source_post_id=source_post_id,
            subreddit=subreddit,
            comments=items,
            source=source,
            source_track="incremental_preview",
            default_business_pool="lab",
            crawl_run_id=crawl_run_id,
        )
    return {"processed": processed, "status": "ok"}


async def run_fetch_and_ingest_post_comments(
    *,
    deps: Any,
    queue: str,
    source_post_id: str,
    subreddit: str,
    mode: str,
    limit: int,
    depth: int,
) -> dict[str, Any]:
    crawl_run_id = str(uuid.uuid4())
    plan = deps.build_backfill_comments_plan(
        source_post_id=source_post_id,
        subreddit=subreddit,
        reason="manual_backfill_comments",
        limit=limit,
        mode=mode,
        depth=depth,
    )
    async with deps.session_factory() as session:
        await deps.ensure_crawler_run(
            session,
            crawl_run_id=crawl_run_id,
            config={
                "mode": "manual_backfill_comments",
                "source": "comments_task",
                "subreddit": subreddit,
                "post_id": source_post_id,
            },
        )
        target_id = await deps.enqueue_backfill_comments_target(
            session=session,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit,
            plan=plan,
            queue=queue,
            ensure_crawler_run_target=deps.ensure_crawler_run_target,
            enqueue_execute_target_outbox=deps.enqueue_execute_target_outbox,
        )
        await session.commit()
    return {"status": "ok", "enqueued": 1, "target_id": target_id, "crawl_run_id": crawl_run_id}


async def run_label_comments_task(
    *,
    deps: Any,
    reddit_comment_ids: list[str],
) -> dict[str, int | str]:
    async with deps.session_factory() as session:
        labeled = await deps.classify_and_label_comments(session, reddit_comment_ids)
        entities = await deps.extract_and_label_entities_for_comments(
            session,
            reddit_comment_ids,
        )
        await session.commit()
    return {"status": "ok", "labeled": labeled, "entities": entities}


async def run_backfill_full_comments(
    *,
    deps: Any,
    queue: str,
    source_post_ids: list[str],
    subreddit: str,
    limit: int,
) -> dict[str, Any]:
    crawl_run_id = str(uuid.uuid4())
    target_ids: list[str] = []
    async with deps.session_factory() as session:
        await deps.ensure_crawler_run(
            session,
            crawl_run_id=crawl_run_id,
            config={
                "mode": "backfill_full_comments",
                "source": "comments_task",
                "subreddit": subreddit,
                "posts": len(source_post_ids),
                "limit": int(limit),
            },
        )
        for post_id in source_post_ids:
            plan = deps.build_backfill_comments_plan(
                source_post_id=post_id,
                subreddit=subreddit,
                reason="backfill_full_comments",
                limit=limit,
                mode="full",
                depth=8,
                label_after_ingest=True,
            )
            target_id = await deps.enqueue_backfill_comments_target(
                session=session,
                crawl_run_id=crawl_run_id,
                subreddit=subreddit,
                plan=plan,
                queue=queue,
                ensure_crawler_run_target=deps.ensure_crawler_run_target,
                enqueue_execute_target_outbox=deps.enqueue_execute_target_outbox,
            )
            target_ids.append(target_id)
        await session.commit()
    return {"status": "ok", "enqueued": len(target_ids), "crawl_run_id": crawl_run_id}


async def run_backfill_recent_full_daily(
    *,
    deps: Any,
    settings: Settings,
    queue: str,
    subreddits_raw: str,
    lookback_days: int,
    per_sub_limit: int,
) -> dict[str, int | str]:
    subreddits = deps.normalize_configured_subreddits(subreddits_raw)
    crawl_run_id = str(uuid.uuid4())
    target_ids: list[str] = []
    if not subreddits:
        return {"status": "ok", "processed": 0, "labeled": 0}

    async with deps.reddit_client_cls(**deps.build_reddit_client_kwargs(settings)) as reddit:
        async with deps.session_factory() as session:
            await deps.ensure_crawler_run(
                session,
                crawl_run_id=crawl_run_id,
                config={
                    "mode": "backfill_recent_full_daily",
                    "source": "comments_task",
                    "subreddits": subreddits,
                    "lookback_days": lookback_days,
                    "per_sub_limit": per_sub_limit,
                },
            )
            for sub in subreddits:
                try:
                    posts = await reddit.fetch_subreddit_posts(
                        sub,
                        limit=per_sub_limit,
                        time_filter="week" if lookback_days > 1 else "day",
                        sort="top",
                    )
                except Exception:
                    continue
                for post in posts:
                    try:
                        plan = deps.build_backfill_comments_plan(
                            source_post_id=str(post.id),
                            subreddit=f"r/{sub}",
                            reason="backfill_recent_full_daily",
                            limit=500,
                            mode="full",
                            depth=8,
                            label_after_ingest=True,
                        )
                        target_id = await deps.enqueue_backfill_comments_target(
                            session=session,
                            crawl_run_id=crawl_run_id,
                            subreddit=f"r/{sub}",
                            plan=plan,
                            queue=queue,
                            ensure_crawler_run_target=deps.ensure_crawler_run_target,
                            enqueue_execute_target_outbox=deps.enqueue_execute_target_outbox,
                        )
                        target_ids.append(target_id)
                    except Exception:
                        try:
                            await session.rollback()
                        except Exception:
                            pass
                        continue
            await session.commit()
    return {
        "status": "ok",
        "processed": 0,
        "labeled": 0,
        "enqueued": len(target_ids),
        "crawl_run_id": crawl_run_id,
    }


async def run_capture_snapshot_daily(
    *,
    deps: Any,
    settings: Settings,
    subreddits_raw: str,
) -> dict[str, int | str]:
    subreddits = deps.normalize_configured_subreddits(subreddits_raw)
    if not subreddits:
        return {"status": "ok", "snapshots": 0}

    async with deps.reddit_client_cls(**deps.build_reddit_client_kwargs(settings)) as reddit:
        async with deps.session_factory() as session:
            count = 0
            for sub in subreddits:
                try:
                    about = await reddit.fetch_subreddit_about(sub)
                    rules = await reddit.fetch_subreddit_rules(sub)
                    ratios = await deps.compute_removal_ratio_by_subreddit(
                        session,
                        since_days=30,
                        subreddits=[sub],
                    )
                    modscore = deps.to_rules_friendliness_score(
                        ratios.get(sub.lower(), 0.0)
                    )
                    await deps.persist_subreddit_snapshot(
                        session,
                        subreddit=sub,
                        subscribers=about.get("subscribers"),
                        active_user_count=about.get("active_user_count"),
                        rules_text=rules,
                        over18=about.get("over18"),
                    )
                    await session.execute(
                        text(
                            """
                            UPDATE subreddit_snapshots SET moderation_score=:score
                            WHERE id = (
                              SELECT id FROM subreddit_snapshots
                              WHERE subreddit=:sub ORDER BY captured_at DESC LIMIT 1
                            )
                            """
                        ),
                        {"score": int(modscore), "sub": sub},
                    )
                    count += 1
                except Exception:
                    continue
            await session.commit()
    return {"status": "ok", "snapshots": count}


async def run_label_posts_recent_task(
    *,
    deps: Any,
    since_days: int,
    limit: int,
) -> dict[str, int | str]:
    async with deps.session_factory() as session:
        result = await deps.label_posts_recent(session, since_days=since_days, limit=limit)
        await session.commit()
    return {"status": "ok", **result}


async def run_backfill_high_value_comments(
    *,
    deps: Any,
    settings: Settings,
    per_sub_limit: int,
    lookback_days: int,
    logger: Any,
) -> dict[str, Any]:
    crawl_run_id = str(uuid.uuid4())
    total_processed = 0
    total_labeled = 0
    total_posts = 0
    failed_subs: list[str] = []
    logger.info(
        "🎯 开始抓取高价值社区的全量评论（每社区%s个帖子，回溯%s天）",
        per_sub_limit,
        lookback_days,
    )
    async with deps.reddit_client_cls(**deps.build_reddit_client_kwargs(settings)) as reddit:
        async with deps.session_factory() as session:
            for sub in deps.high_value_subreddits:
                try:
                    logger.info("📥 正在抓取 r/%s 的帖子...", sub)
                    posts = await reddit.fetch_subreddit_posts(
                        sub,
                        limit=per_sub_limit,
                        time_filter=deps.select_time_filter(lookback_days),
                        sort="top",
                    )
                    total_posts += len(posts)
                    for post in posts:
                        try:
                            items = await reddit.fetch_post_comments(
                                post.id,
                                sort="confidence",
                                depth=8,
                                limit=500,
                                mode="full",
                            )
                            if not items:
                                continue
                            await deps.persist_comments(
                                session,
                                source_post_id=post.id,
                                subreddit=sub,
                                comments=items,
                                crawl_run_id=crawl_run_id,
                            )
                            ids = [item.get("id") for item in items if item.get("id")]
                            total_labeled += await deps.classify_and_label_comments(session, ids)
                            total_labeled += await deps.extract_and_label_entities_for_comments(
                                session,
                                ids,
                            )
                            total_processed += len(items)
                            await session.commit()
                        except Exception as exc:
                            try:
                                await session.rollback()
                            except Exception:
                                pass
                            logger.warning("  ✗ 帖子 %s 评论抓取失败: %s", post.id, exc)
                            continue
                except Exception as exc:
                    logger.error("❌ r/%s 抓取失败: %s", sub, exc)
                    failed_subs.append(sub)
                    continue
    return {
        "status": "ok",
        "processed": total_processed,
        "labeled": total_labeled,
        "total_posts": total_posts,
        "total_subreddits": len(deps.high_value_subreddits),
        "failed_subreddits": failed_subs,
    }


__all__ = [
    "build_comments_task_runtime_deps",
    "run_backfill_full_comments",
    "run_backfill_high_value_comments",
    "run_backfill_recent_full_daily",
    "run_capture_snapshot_daily",
    "run_fetch_and_ingest_post_comments",
    "run_ingest_post_comments",
    "run_label_comments_task",
    "run_label_posts_recent_task",
]
