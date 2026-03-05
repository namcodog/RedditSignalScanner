from __future__ import annotations

import hashlib
import json
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_pool import CommunityPool
from app.models.discovered_community import DiscoveredCommunity
from app.models.evidence_post import EvidencePost
from app.services.crawl.plan_contract import CrawlPlanContract
from app.services.crawl.comments_ingest import persist_comments
from app.services.labeling.labeling_service import (
    classify_and_label_comments,
    extract_and_label_entities_for_comments,
)
from app.services.crawl.incremental_crawler import IncrementalCrawler
from app.services.discovery.warzone_classifier import WarzoneClassifier
from app.services.infrastructure.reddit_client import RedditAPIClient
from app.utils.subreddit import subreddit_key


async def execute_crawl_plan(
    *,
    plan: CrawlPlanContract,
    session: AsyncSession,
    reddit_client: RedditAPIClient,
    crawl_run_id: str,
    community_run_id: str,
) -> dict[str, object]:
    """
    统一执行器（v1）：给定一张 CrawlPlan 合同，执行并返回结果。

    说明：
    - 这是“收口”的关键：巡航/补数最终都走同一段执行逻辑。
    - 语义/探针/评论回填会在后续逐步接进来。
    """
    if plan.plan_kind == "patrol":
        # ✅ Executor 侧二次护栏：不信任 plan/config，强制夹住巡航配额
        posts_limit = int(plan.limits.posts_limit or 80)
        posts_limit = max(1, min(100, posts_limit))

        raw_time_filter = str(plan.meta.get("time_filter") or "day").strip().lower()
        # 巡航只允许更窄窗口（hour/day），避免“抓到爽”把历史当巡航跑
        time_filter = raw_time_filter if raw_time_filter in {"hour", "day"} else "day"
        sort = str(plan.meta.get("sort") or "top")
        hot_cache_ttl_hours = int(plan.meta.get("hot_cache_ttl_hours") or 4320)

        crawler = IncrementalCrawler(
            db=session,
            reddit_client=reddit_client,
            hot_cache_ttl_hours=hot_cache_ttl_hours,
            crawl_run_id=crawl_run_id,
            community_run_id=community_run_id,
            source_track="incremental",
        )
        result = await crawler.crawl_community_incremental(
            plan.target_value,
            limit=posts_limit,
            time_filter=time_filter,
            sort=sort,
        )
        return dict(result)

    if plan.plan_kind == "backfill_posts":
        if plan.window is None or plan.window.since is None or plan.window.until is None:
            raise ValueError("backfill_posts requires window.since and window.until")
        max_posts = int(plan.limits.posts_limit or 1000)
        cursor_after = str(plan.meta.get("cursor_after") or "").strip() or None

        crawler = IncrementalCrawler(
            db=session,
            reddit_client=reddit_client,
            crawl_run_id=crawl_run_id,
            community_run_id=community_run_id,
            source_track="backfill_posts",
            refresh_posts_latest_after_write=False,
        )
        result = await crawler.backfill_posts_window(
            plan.target_value,
            since=plan.window.since,
            until=plan.window.until,
            max_posts=max_posts,
            sort=str(plan.meta.get("sort") or "new"),
            after=cursor_after,
        )
        return dict(result)

    if plan.plan_kind in {
        "seed_top_year",
        "seed_top_all",
        "seed_controversial_year",
    }:
        max_posts = int(plan.limits.posts_limit or 1000)
        max_posts = max(1, min(1000, max_posts))
        cursor_after = str(plan.meta.get("cursor_after") or "").strip() or None

        sort = "top"
        time_filter = "year"
        if plan.plan_kind == "seed_top_all":
            time_filter = "all"
        if plan.plan_kind == "seed_controversial_year":
            sort = "controversial"
            time_filter = "year"

        crawler = IncrementalCrawler(
            db=session,
            reddit_client=reddit_client,
            crawl_run_id=crawl_run_id,
            community_run_id=community_run_id,
            source_track=str(plan.plan_kind),
            refresh_posts_latest_after_write=False,
            enable_comments_backfill=True,
            comments_backfill_mode="smart_shallow",
            comments_backfill_limit=50,
            comments_backfill_depth=2,
        )

        start_time = datetime.now(timezone.utc)
        posts: list[Any] = []
        next_after = cursor_after
        while len(posts) < max_posts:
            batch_limit = min(100, max_posts - len(posts))
            batch, batch_after = await reddit_client.fetch_subreddit_posts(
                plan.target_value,
                limit=batch_limit,
                time_filter=time_filter,
                sort=sort,
                after=next_after,
            )
            if not batch:
                break
            posts.extend(batch)
            if not batch_after:
                next_after = None
                break
            next_after = batch_after

        if not posts:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            return {
                "plan_kind": plan.plan_kind,
                "status": "completed",
                "total_fetched": 0,
                "unique_posts": 0,
                "new_posts": 0,
                "updated_posts": 0,
                "duplicates": 0,
                "duration_seconds": duration,
                "max_seen_created_at": None,
                "min_seen_created_at": None,
            }

        new_count, updated_count, dup_count = await crawler._dual_write(
            plan.target_value, posts, trigger_comments_fetch=True
        )

        max_post = max(posts, key=lambda p: p.created_utc)
        min_post = min(posts, key=lambda p: p.created_utc)
        max_seen = datetime.fromtimestamp(max_post.created_utc, tz=timezone.utc)
        min_seen = datetime.fromtimestamp(min_post.created_utc, tz=timezone.utc)

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        return {
            "plan_kind": plan.plan_kind,
            "status": "completed",
            "total_fetched": len(posts),
            "unique_posts": len(posts),
            "new_posts": new_count,
            "updated_posts": updated_count,
            "duplicates": dup_count,
            "duration_seconds": duration,
            "max_seen_created_at": max_seen.isoformat(),
            "min_seen_created_at": min_seen.isoformat(),
        }

    if plan.plan_kind == "probe":
        source = str(plan.meta.get("source") or "").strip().lower()
        if source not in {"search", "hot"}:
            raise ValueError("probe requires meta.source in {'search','hot'}")

        now = datetime.now(timezone.utc)
        target_value = plan.target_value.strip()
        raw_posts_limit = int(plan.limits.posts_limit or 10)

        # Reddit search API caps at 100; hot probe is intentionally smaller.
        max_posts_limit = 100 if source == "search" else 50
        posts_limit = max(1, min(max_posts_limit, raw_posts_limit))

        max_candidate_subreddits = int(
            plan.meta.get("max_candidate_subreddits")
            or plan.meta.get("max_discovered_communities")
            or (30 if source == "hot" else 50)
        )
        max_candidate_subreddits = max(1, min(100, max_candidate_subreddits))

        if source == "search":
            max_evidence_posts = int(plan.meta.get("max_evidence_posts") or posts_limit)
            max_evidence_posts = max(1, min(posts_limit, max_evidence_posts))
            max_evidence_per_subreddit = int(
                plan.meta.get("max_evidence_per_subreddit") or max_evidence_posts
            )
            max_evidence_per_subreddit = max(
                1, min(max_evidence_posts, max_evidence_per_subreddit)
            )
        else:
            max_evidence_per_subreddit = int(plan.meta.get("max_evidence_per_subreddit") or 3)
            max_evidence_per_subreddit = max(1, min(5, max_evidence_per_subreddit))
            default_total_evidence_cap = max_candidate_subreddits * max_evidence_per_subreddit
            max_evidence_posts = int(
                plan.meta.get("max_evidence_posts") or default_total_evidence_cap
            )
            max_evidence_posts = max(1, min(default_total_evidence_cap, max_evidence_posts))

        min_score = int(plan.meta.get("min_score") or (100 if source == "hot" else 0))
        min_comments = int(plan.meta.get("min_comments") or (30 if source == "hot" else 0))
        max_age_hours = plan.meta.get("max_age_hours")
        if max_age_hours is None:
            max_age_hours = 72 if source == "hot" else 0
        max_age_hours = int(max_age_hours or 0)
        if max_age_hours > 0:
            max_age_hours = max(24, min(168, max_age_hours))

        def _query_hash(value: str) -> str:
            raw = value.strip().encode("utf-8")
            return hashlib.sha256(raw).hexdigest()

        def _evidence_score(*, score: int, num_comments: int) -> int:
            return max(0, int(score)) + max(0, int(num_comments)) * 2

        def _is_obvious_spam(*, title: str, body: str) -> bool:
            text = f"{title}\n{body}".lower()
            # Very small, conservative heuristics (can be expanded later).
            spam_terms = (
                "affiliate",
                "referral",
                "sponsored",
                "coupon code",
                "discount code",
                "giveaway",
                "promo code",
            )
            if any(t in text for t in spam_terms) and ("http://" in text or "https://" in text):
                return True
            return False

        fetched_posts: list[Any] = []
        source_query = ""
        if source == "search":
            query = target_value
            time_filter = str(plan.meta.get("time_filter") or "week")
            sort = str(plan.meta.get("sort") or "relevance")
            fetched_posts = await reddit_client.search_posts(
                query=query,
                limit=posts_limit,
                time_filter=time_filter,
                sort=sort,
            )
            source_query = query
        else:
            # Hot probe supports multiple feeds in one plan (Key 拍板：统一入口+总量可控).
            raw_sources = plan.meta.get("hot_sources") or []
            hot_sources: list[dict[str, str]] = []
            if isinstance(raw_sources, list):
                for item in raw_sources:
                    if isinstance(item, str):
                        hot_sources.append({"subreddit": subreddit_key(item), "sort": "hot"})
                    elif isinstance(item, dict):
                        sub = subreddit_key(str(item.get("subreddit") or ""))
                        if not sub:
                            continue
                        hot_sources.append(
                            {
                                "subreddit": sub,
                                "sort": str(item.get("sort") or "hot"),
                                "time_filter": str(item.get("time_filter") or "day"),
                            }
                        )
            if not hot_sources:
                # Backward-compatible single-source form: use target_value as the feed.
                hot_sources = [{"subreddit": subreddit_key(target_value), "sort": "hot"}]

            # Hard clamp: prevent list explosion
            hot_sources = hot_sources[:20]
            source_query = json.dumps(hot_sources, ensure_ascii=False, sort_keys=True)

            for feed in hot_sources:
                sub = feed.get("subreddit") or ""
                if not sub:
                    continue
                sort = feed.get("sort") or "hot"
                time_filter = feed.get("time_filter") or "day"
                posts, _after = await reddit_client.fetch_subreddit_posts(
                    subreddit=sub,
                    limit=posts_limit,
                    sort=sort,
                    time_filter=time_filter,
                )
                fetched_posts.extend(posts)

        # Dedup by post id first, then take Top-N by evidence_score for determinism.
        seen_ids: set[str] = set()
        unique_posts: list[Any] = []
        for p in fetched_posts:
            pid = str(getattr(p, "id", "") or "").strip()
            if not pid or pid in seen_ids:
                continue
            seen_ids.add(pid)
            unique_posts.append(p)

        # Filter + scoring.
        per_sub_posts: defaultdict[str, list[tuple[int, float, Any]]] = defaultdict(list)
        scored_posts: list[tuple[int, float, Any, str]] = []
        for p in unique_posts:
            score = int(getattr(p, "score", 0) or 0)
            num_comments = int(getattr(p, "num_comments", 0) or 0)

            created_utc = float(getattr(p, "created_utc", 0.0) or 0.0)
            created_at = None
            if created_utc > 0:
                try:
                    created_at = datetime.fromtimestamp(created_utc, tz=timezone.utc)
                except Exception:
                    created_at = None

            if max_age_hours > 0 and created_at is not None:
                if created_at < now - timedelta(hours=max_age_hours):
                    continue

            # Threshold gate: score>=min_score OR comments>=min_comments
            if (min_score > 0 or min_comments > 0) and (score < min_score and num_comments < min_comments):
                continue

            title = str(getattr(p, "title", "") or "")
            body = str(getattr(p, "selftext", "") or "")
            if _is_obvious_spam(title=title, body=body):
                continue

            sub = subreddit_key(str(getattr(p, "subreddit", "") or ""))
            ev = _evidence_score(score=score, num_comments=num_comments)
            per_sub_posts[sub].append((ev, created_utc, p))
            scored_posts.append((ev, created_utc, p, sub))

        truncated = False
        picked_subs: list[str] = []
        top_posts: list[Any] = []
        candidate_scores: defaultdict[str, int] = defaultdict(int)

        if source == "search":
            # Search: evidence_posts 是审计资产（Top-N），不应该被候选社区上限“连坐”砍掉。
            # 先选证据帖（最多 max_evidence_posts），再从证据帖里挑 Top-K 社区写 discovered_communities。
            scored_posts.sort(key=lambda it: (it[0], it[1], it[3]), reverse=True)

            per_sub_count: defaultdict[str, int] = defaultdict(int)
            selected_rows: list[tuple[int, float, Any, str]] = []
            for ev, created_utc, p, sub in scored_posts:
                if len(selected_rows) >= max_evidence_posts:
                    truncated = True
                    break
                if per_sub_count[sub] >= max_evidence_per_subreddit:
                    truncated = True
                    continue
                per_sub_count[sub] += 1
                selected_rows.append((ev, created_utc, p, sub))

            top_posts = [p for _ev, _ts, p, _sub in selected_rows]
            for ev, _ts, _p, sub in selected_rows:
                candidate_scores[sub] += ev

            ranked_candidates = sorted(
                candidate_scores.items(), key=lambda kv: (kv[1], kv[0]), reverse=True
            )
            if len(ranked_candidates) > max_candidate_subreddits:
                truncated = True
            picked_subs = [sub for sub, _score in ranked_candidates[:max_candidate_subreddits]]
        else:
            # Hot: 先按社区聚合打分（公平），再按每社区上限挑证据帖，避免被单个大社区“刷屏”。
            for sub, rows in per_sub_posts.items():
                candidate_scores[sub] = sum(ev for ev, _ts, _p in rows)

            ranked_candidates = sorted(
                candidate_scores.items(), key=lambda kv: (kv[1], kv[0]), reverse=True
            )
            truncated = len(ranked_candidates) > max_candidate_subreddits
            picked_subs = [sub for sub, _score in ranked_candidates[:max_candidate_subreddits]]

            selected: list[Any] = []
            for sub in picked_subs:
                rows = per_sub_posts.get(sub) or []
                rows.sort(key=lambda it: (it[0], it[1]), reverse=True)
                if len(rows) > max_evidence_per_subreddit:
                    truncated = True
                selected.extend([p for _ev, _ts, p in rows[:max_evidence_per_subreddit]])

            # Global cap (should usually equal max_candidate_subreddits * max_evidence_per_subreddit)
            scored_selected: list[tuple[int, float, Any]] = []
            for p in selected:
                score = int(getattr(p, "score", 0) or 0)
                num_comments = int(getattr(p, "num_comments", 0) or 0)
                created_utc = float(getattr(p, "created_utc", 0.0) or 0.0)
                scored_selected.append(
                    (_evidence_score(score=score, num_comments=num_comments), created_utc, p)
                )
            scored_selected.sort(key=lambda it: (it[0], it[1]), reverse=True)
            if len(scored_selected) > max_evidence_posts:
                truncated = True
            top_posts = [p for _ev, _ts, p in scored_selected[:max_evidence_posts]]

        q_hash = _query_hash(source_query)
        try:
            crawl_run_uuid = uuid.UUID(str(crawl_run_id))
        except Exception:
            crawl_run_uuid = None
        try:
            target_uuid = uuid.UUID(str(community_run_id))
        except Exception:
            target_uuid = None

        evidence_values: list[dict[str, Any]] = []
        for p in top_posts:
            sub = subreddit_key(str(getattr(p, "subreddit", "") or ""))
            score = int(getattr(p, "score", 0) or 0)
            num_comments = int(getattr(p, "num_comments", 0) or 0)
            ev = _evidence_score(score=score, num_comments=num_comments)
            post_created_at: datetime | None = None
            try:
                created_utc = float(getattr(p, "created_utc", 0.0) or 0.0)
                if created_utc > 0:
                    post_created_at = datetime.fromtimestamp(created_utc, tz=timezone.utc)
            except Exception:
                post_created_at = None

            evidence_values.append(
                {
                    "crawl_run_id": crawl_run_uuid,
                    "target_id": target_uuid,
                    "probe_source": source,
                    "source_query": source_query,
                    "source_query_hash": q_hash,
                    "source_post_id": str(getattr(p, "id", "") or ""),
                    "subreddit": sub,
                    "title": str(getattr(p, "title", "") or ""),
                    "summary": str(getattr(p, "selftext", "") or "") or None,
                    "score": score,
                    "num_comments": num_comments,
                    "post_created_at": post_created_at,
                    "evidence_score": ev,
                }
            )

        inserted_counts: Counter[str] = Counter()
        if evidence_values:
            insert_stmt = (
                pg_insert(EvidencePost)
                .values(evidence_values)
                .on_conflict_do_nothing(
                    index_elements=[
                        EvidencePost.probe_source,
                        EvidencePost.source_query_hash,
                        EvidencePost.source_post_id,
                    ]
                )
                .returning(EvidencePost.subreddit, EvidencePost.evidence_score)
            )
            rows = (await session.execute(insert_stmt)).all()
            for subreddit, evidence_score in rows:
                key = str(subreddit or "")
                if not key:
                    continue
                inserted_counts[key] += 1

        # Step 8 (warzone v0): classify candidates using evidence posts (purely heuristic, best-effort).
        texts_by_sub: defaultdict[str, list[str]] = defaultdict(list)
        for ev in evidence_values:
            try:
                sub = str(ev.get("subreddit") or "")
                title = str(ev.get("title") or "")
                summary = str(ev.get("summary") or "") if ev.get("summary") else ""
                if sub:
                    texts_by_sub[sub].append(f"{title}\n{summary}".strip())
            except Exception:
                continue

        warzone_by_sub: dict[str, object] = {}
        try:
            cfg_path = Path("backend/config/warzones.yaml")
            clf = WarzoneClassifier(cfg_path)
        except Exception:
            clf = None
        if clf is not None:
            for sub in picked_subs:
                try:
                    guess = clf.classify_texts(texts_by_sub.get(sub, []))
                    if guess.warzone and guess.warzone != "unknown" and float(guess.confidence) > 0:
                        warzone_by_sub[sub] = guess
                except Exception:
                    continue

        upserted = 0
        for name in picked_subs:
            # discovered_communities.name has FK to community_pool.name in prod schema:
            # ensure the pool row exists first (as candidate) to avoid insert failures.
            await session.execute(
                pg_insert(CommunityPool)
                .values(
                    name=name,
                    tier="candidate",
                    categories={},
                    description_keywords={
                        "probe_source": source,
                        "source_query": source_query,
                        "source_query_hash": q_hash,
                    },
                    # 发现社区只做“候选记录”，默认不激活，避免污染正式社区池
                    is_active=False,
                )
                .on_conflict_do_nothing(index_elements=[CommunityPool.name])
            )

            inc = int(inserted_counts.get(name, 0))
            payload = {
                "probe_source": source,
                "source_query": source_query,
                "source_query_hash": q_hash,
                "evidence_score_sum": int(candidate_scores.get(name, 0)),
                "inserted_evidence_posts": inc,
                "ts": now.isoformat(),
            }
            stmt = (
                pg_insert(DiscoveredCommunity)
                .values(
                    name=name,
                    discovered_from_keywords=payload,
                    discovered_count=inc,
                    first_discovered_at=now,
                    last_discovered_at=now,
                    status="pending",
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=[DiscoveredCommunity.name],
                    set_={
                        "discovered_count": DiscoveredCommunity.discovered_count + inc,
                        "last_discovered_at": now,
                        "updated_at": now,
                    },
                )
            )
            await session.execute(stmt)
            upserted += 1

            # Best-effort warzone writeback (non-blocking)
            guess = warzone_by_sub.get(name)
            if guess is not None:
                try:
                    wz = str(getattr(guess, "warzone", "") or "")
                    if wz and wz != "unknown":
                        tag = f"warzone:{wz}"
                        payload2 = json.dumps(
                            {
                                "warzone_guess": wz,
                                "confidence": float(getattr(guess, "confidence", 0.0) or 0.0),
                                "reasons": list(getattr(guess, "reasons", []) or []),
                                "ts": now.isoformat(),
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                        await session.execute(
                            text(
                                """
                                UPDATE discovered_communities
                                SET metrics = jsonb_set(COALESCE(metrics,'{}'::jsonb), '{warzone}', CAST(:payload AS jsonb), true),
                                    tags = CASE
                                        WHEN tags IS NULL THEN ARRAY[:tag]::varchar[]
                                        WHEN :tag = ANY(tags) THEN tags
                                        ELSE array_append(tags, :tag)
                                    END,
                                    updated_at = NOW()
                                WHERE name = :name
                                """
                            ),
                            {"name": name, "tag": tag, "payload": payload2},
                        )
                except Exception:
                    pass

        return {
            "plan_kind": "probe",
            "source": source,
            "query": source_query,
            "status": "partial" if truncated else "completed",
            "reason": "caps_reached" if truncated else None,
            "evidence_posts_fetched": len(unique_posts),
            "evidence_posts_written": sum(inserted_counts.values()),
            "discovered_communities_upserted": upserted,
        }

    if plan.plan_kind == "backfill_comments":
        # 口径：一张 plan = 一个 post_id 的评论回填
        post_id = str(plan.target_value or "").strip()
        subreddit = subreddit_key(str(plan.meta.get("subreddit") or ""))
        if not post_id:
            raise ValueError("backfill_comments requires target_value (post_id)")
        post_score: int | None = None
        post_num_comments: int | None = None
        post_created_at: datetime | None = None

        if post_id.isdigit():
            # If a numeric internal post id was mistakenly supplied, resolve it to source_post_id.
            try:
                internal_id = int(post_id)
            except ValueError:
                internal_id = None
            if internal_id is not None:
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
                resolved = row.first()
                if resolved:
                    resolved_post_id = str(resolved[0] or "").strip()
                    if resolved_post_id:
                        post_id = resolved_post_id
                    if not subreddit:
                        subreddit = subreddit_key(str(resolved[1] or ""))
                    try:
                        post_score = int(resolved[2]) if resolved[2] is not None else None
                    except (TypeError, ValueError):
                        post_score = None
                    try:
                        post_num_comments = (
                            int(resolved[3]) if resolved[3] is not None else None
                        )
                    except (TypeError, ValueError):
                        post_num_comments = None
                    post_created_at = resolved[4] if len(resolved) > 4 else None
        if not subreddit:
            raise ValueError("backfill_comments requires meta.subreddit")

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
                {"pid": post_id},
            )
            resolved = row.first()
            if resolved:
                try:
                    post_score = int(resolved[0]) if resolved[0] is not None else None
                except (TypeError, ValueError):
                    post_score = None
                try:
                    post_num_comments = (
                        int(resolved[1]) if resolved[1] is not None else None
                    )
                except (TypeError, ValueError):
                    post_num_comments = None
                post_created_at = resolved[2] if len(resolved) > 2 else None

        if post_created_at is not None and getattr(post_created_at, "tzinfo", None) is None:
            post_created_at = post_created_at.replace(tzinfo=timezone.utc)

        if post_num_comments is not None:
            if post_num_comments <= 0:
                return {
                    "plan_kind": "backfill_comments",
                    "status": "completed",
                    "processed": 0,
                    "reason": "no_comments",
                }
            if post_num_comments <= 500:
                existing = await session.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM comments
                        WHERE source = 'reddit' AND source_post_id = :pid
                        """
                    ),
                    {"pid": post_id},
                )
                existing_count = int(existing.scalar_one() or 0)
                if existing_count >= post_num_comments:
                    return {
                        "plan_kind": "backfill_comments",
                        "status": "completed",
                        "processed": 0,
                        "reason": "already_up_to_date",
                    }

        raw_limit = int(plan.limits.comments_limit or 50)
        comments_limit = max(1, min(500, raw_limit))
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

        items = await reddit_client.fetch_post_comments(
            post_id,
            sort=sort,
            depth=depth,
            limit=comments_limit,
            mode=mode,
            smart_config=smart_config,
        )
        processed = await persist_comments(
            session,
            source_post_id=post_id,
            subreddit=subreddit,
            comments=items,
            crawl_run_id=crawl_run_id,
            community_run_id=community_run_id,
            source_track="backfill_comments",
            default_business_pool="lab",
        )
        labeled = 0
        if bool(plan.meta.get("label_after_ingest")):
            ids = [str(c.get("id")) for c in items if c.get("id")]
            if ids:
                labeled += await classify_and_label_comments(session, ids)
                labeled += await extract_and_label_entities_for_comments(session, ids)
        return {
            "plan_kind": "backfill_comments",
            "status": "completed",
            "processed": int(processed or 0),
            "labeled": int(labeled or 0),
        }

    raise ValueError(f"Unsupported plan_kind: {plan.plan_kind}")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = ["execute_crawl_plan", "utc_now_iso"]
