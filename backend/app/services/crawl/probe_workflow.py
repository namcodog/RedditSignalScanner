from __future__ import annotations

import hashlib
import json
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_pool import CommunityPool
from app.models.discovered_community import DiscoveredCommunity
from app.models.evidence_post import EvidencePost
from app.services.crawl.plan_contract import CrawlPlanContract
from app.services.discovery.warzone_classifier import WarzoneClassifier
from app.services.infrastructure.reddit_client import RedditAPIClient
from app.utils.subreddit import subreddit_key


def _default_spam_checker(title: str, body: str) -> bool:
    text = f"{title}\n{body}".lower()
    spam_terms = (
        "affiliate",
        "referral",
        "sponsored",
        "coupon code",
        "discount code",
        "giveaway",
        "promo code",
    )
    return any(term in text for term in spam_terms) and (
        "http://" in text or "https://" in text
    )


@dataclass(slots=True)
class ProbeWorkflowInput:
    plan: CrawlPlanContract
    session: AsyncSession
    reddit_client: RedditAPIClient
    crawl_run_id: str
    community_run_id: str


@dataclass(slots=True)
class ProbeWorkflowDeps:
    now_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    query_hash_fn: Callable[[str], str] = lambda value: hashlib.sha256(
        value.strip().encode("utf-8")
    ).hexdigest()
    evidence_score_fn: Callable[[int, int], int] = (
        lambda score, num_comments: max(0, int(score)) + max(0, int(num_comments)) * 2
    )
    spam_checker: Callable[[str, str], bool] = _default_spam_checker
    warzone_config_path: Path = field(default_factory=lambda: Path("backend/config/warzones.yaml"))


@dataclass(slots=True)
class ProbeWorkflowResult:
    payload: dict[str, object]


def _coerce_probe_limits(*, plan: CrawlPlanContract, source: str) -> tuple[int, int, int, int, int]:
    raw_posts_limit = int(plan.limits.posts_limit or 10)
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
        max_evidence_per_subreddit = max(1, min(max_evidence_posts, max_evidence_per_subreddit))
    else:
        max_evidence_per_subreddit = int(plan.meta.get("max_evidence_per_subreddit") or 3)
        max_evidence_per_subreddit = max(1, min(5, max_evidence_per_subreddit))
        default_total_evidence_cap = max_candidate_subreddits * max_evidence_per_subreddit
        max_evidence_posts = int(plan.meta.get("max_evidence_posts") or default_total_evidence_cap)
        max_evidence_posts = max(1, min(default_total_evidence_cap, max_evidence_posts))

    return (
        posts_limit,
        max_candidate_subreddits,
        max_evidence_posts,
        max_evidence_per_subreddit,
        max_posts_limit,
    )


async def _fetch_probe_posts(
    *,
    workflow_input: ProbeWorkflowInput,
    source: str,
    posts_limit: int,
) -> tuple[list[Any], str]:
    plan = workflow_input.plan
    target_value = plan.target_value.strip()

    if source == "search":
        query = target_value
        time_filter = str(plan.meta.get("time_filter") or "week")
        sort = str(plan.meta.get("sort") or "relevance")
        posts = await workflow_input.reddit_client.search_posts(
            query=query,
            limit=posts_limit,
            time_filter=time_filter,
            sort=sort,
        )
        return posts, query

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
        hot_sources = [{"subreddit": subreddit_key(target_value), "sort": "hot"}]

    hot_sources = hot_sources[:20]
    fetched_posts: list[Any] = []
    for feed in hot_sources:
        sub = feed.get("subreddit") or ""
        if not sub:
            continue
        sort = feed.get("sort") or "hot"
        time_filter = feed.get("time_filter") or "day"
        posts, _after = await workflow_input.reddit_client.fetch_subreddit_posts(
            subreddit=sub,
            limit=posts_limit,
            sort=sort,
            time_filter=time_filter,
        )
        fetched_posts.extend(posts)
    return fetched_posts, json.dumps(hot_sources, ensure_ascii=False, sort_keys=True)


def _dedupe_and_score_posts(
    *,
    fetched_posts: list[Any],
    now: datetime,
    source: str,
    min_score: int,
    min_comments: int,
    max_age_hours: int,
    evidence_score_fn: Callable[[int, int], int],
    spam_checker: Callable[[str, str], bool],
) -> tuple[list[Any], defaultdict[str, list[tuple[int, float, Any]]], list[tuple[int, float, Any, str]]]:
    seen_ids: set[str] = set()
    unique_posts: list[Any] = []
    for post in fetched_posts:
        pid = str(getattr(post, "id", "") or "").strip()
        if not pid or pid in seen_ids:
            continue
        seen_ids.add(pid)
        unique_posts.append(post)

    per_sub_posts: defaultdict[str, list[tuple[int, float, Any]]] = defaultdict(list)
    scored_posts: list[tuple[int, float, Any, str]] = []
    for post in unique_posts:
        score = int(getattr(post, "score", 0) or 0)
        num_comments = int(getattr(post, "num_comments", 0) or 0)

        created_utc = float(getattr(post, "created_utc", 0.0) or 0.0)
        created_at = None
        if created_utc > 0:
            try:
                created_at = datetime.fromtimestamp(created_utc, tz=timezone.utc)
            except Exception:
                created_at = None

        if max_age_hours > 0 and created_at is not None:
            if created_at < now - timedelta(hours=max_age_hours):
                continue

        if (min_score > 0 or min_comments > 0) and (score < min_score and num_comments < min_comments):
            continue

        title = str(getattr(post, "title", "") or "")
        body = str(getattr(post, "selftext", "") or "")
        if spam_checker(title, body):
            continue

        sub = subreddit_key(str(getattr(post, "subreddit", "") or ""))
        evidence_score = evidence_score_fn(score, num_comments)
        per_sub_posts[sub].append((evidence_score, created_utc, post))
        scored_posts.append((evidence_score, created_utc, post, sub))

    return unique_posts, per_sub_posts, scored_posts


def _select_probe_candidates(
    *,
    source: str,
    scored_posts: list[tuple[int, float, Any, str]],
    per_sub_posts: defaultdict[str, list[tuple[int, float, Any]]],
    max_candidate_subreddits: int,
    max_evidence_posts: int,
    max_evidence_per_subreddit: int,
    evidence_score_fn: Callable[[int, int], int],
) -> tuple[bool, list[str], list[Any], defaultdict[str, int]]:
    truncated = False
    picked_subs: list[str] = []
    top_posts: list[Any] = []
    candidate_scores: defaultdict[str, int] = defaultdict(int)

    if source == "search":
        scored_posts.sort(key=lambda item: (item[0], item[1], item[3]), reverse=True)
        per_sub_count: defaultdict[str, int] = defaultdict(int)
        selected_rows: list[tuple[int, float, Any, str]] = []
        for evidence_score, created_utc, post, sub in scored_posts:
            if len(selected_rows) >= max_evidence_posts:
                truncated = True
                break
            if per_sub_count[sub] >= max_evidence_per_subreddit:
                truncated = True
                continue
            per_sub_count[sub] += 1
            selected_rows.append((evidence_score, created_utc, post, sub))

        top_posts = [post for _ev, _ts, post, _sub in selected_rows]
        for evidence_score, _ts, _post, sub in selected_rows:
            candidate_scores[sub] += evidence_score

        ranked_candidates = sorted(
            candidate_scores.items(), key=lambda item: (item[1], item[0]), reverse=True
        )
        if len(ranked_candidates) > max_candidate_subreddits:
            truncated = True
        picked_subs = [sub for sub, _score in ranked_candidates[:max_candidate_subreddits]]
        return truncated, picked_subs, top_posts, candidate_scores

    for sub, rows in per_sub_posts.items():
        candidate_scores[sub] = sum(evidence_score for evidence_score, _ts, _post in rows)

    ranked_candidates = sorted(
        candidate_scores.items(), key=lambda item: (item[1], item[0]), reverse=True
    )
    truncated = len(ranked_candidates) > max_candidate_subreddits
    picked_subs = [sub for sub, _score in ranked_candidates[:max_candidate_subreddits]]

    selected: list[Any] = []
    for sub in picked_subs:
        rows = per_sub_posts.get(sub) or []
        rows.sort(key=lambda item: (item[0], item[1]), reverse=True)
        if len(rows) > max_evidence_per_subreddit:
            truncated = True
        selected.extend([post for _ev, _ts, post in rows[:max_evidence_per_subreddit]])

    scored_selected: list[tuple[int, float, Any]] = []
    for post in selected:
        score = int(getattr(post, "score", 0) or 0)
        num_comments = int(getattr(post, "num_comments", 0) or 0)
        created_utc = float(getattr(post, "created_utc", 0.0) or 0.0)
        scored_selected.append((evidence_score_fn(score, num_comments), created_utc, post))
    scored_selected.sort(key=lambda item: (item[0], item[1]), reverse=True)
    if len(scored_selected) > max_evidence_posts:
        truncated = True
    top_posts = [post for _ev, _ts, post in scored_selected[:max_evidence_posts]]
    return truncated, picked_subs, top_posts, candidate_scores


async def _persist_probe_results(
    *,
    workflow_input: ProbeWorkflowInput,
    source: str,
    source_query: str,
    q_hash: str,
    now: datetime,
    top_posts: list[Any],
    picked_subs: list[str],
    candidate_scores: defaultdict[str, int],
    evidence_score_fn: Callable[[int, int], int],
    warzone_config_path: Path,
) -> tuple[Counter[str], int]:
    try:
        crawl_run_uuid = uuid.UUID(str(workflow_input.crawl_run_id))
    except Exception:
        crawl_run_uuid = None
    try:
        target_uuid = uuid.UUID(str(workflow_input.community_run_id))
    except Exception:
        target_uuid = None

    evidence_values: list[dict[str, Any]] = []
    texts_by_sub: defaultdict[str, list[str]] = defaultdict(list)
    for post in top_posts:
        sub = subreddit_key(str(getattr(post, "subreddit", "") or ""))
        score = int(getattr(post, "score", 0) or 0)
        num_comments = int(getattr(post, "num_comments", 0) or 0)
        evidence_score = evidence_score_fn(score, num_comments)
        post_created_at: datetime | None = None
        try:
            created_utc = float(getattr(post, "created_utc", 0.0) or 0.0)
            if created_utc > 0:
                post_created_at = datetime.fromtimestamp(created_utc, tz=timezone.utc)
        except Exception:
            post_created_at = None

        title = str(getattr(post, "title", "") or "")
        summary = str(getattr(post, "selftext", "") or "")
        evidence_values.append(
            {
                "crawl_run_id": crawl_run_uuid,
                "target_id": target_uuid,
                "probe_source": source,
                "source_query": source_query,
                "source_query_hash": q_hash,
                "source_post_id": str(getattr(post, "id", "") or ""),
                "subreddit": sub,
                "title": title,
                "summary": summary or None,
                "score": score,
                "num_comments": num_comments,
                "post_created_at": post_created_at,
                "evidence_score": evidence_score,
            }
        )
        if sub:
            texts_by_sub[sub].append(f"{title}\n{summary}".strip())

    inserted_counts: Counter[str] = Counter()
    session = workflow_input.session
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
        for subreddit, _evidence_score in rows:
            key = str(subreddit or "")
            if key:
                inserted_counts[key] += 1

    warzone_by_sub: dict[str, object] = {}
    try:
        classifier = WarzoneClassifier(warzone_config_path)
    except Exception:
        classifier = None
    if classifier is not None:
        for sub in picked_subs:
            try:
                guess = classifier.classify_texts(texts_by_sub.get(sub, []))
                if guess.warzone and guess.warzone != "unknown" and float(guess.confidence) > 0:
                    warzone_by_sub[sub] = guess
            except Exception:
                continue

    upserted = 0
    for name in picked_subs:
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
                is_active=False,
            )
            .on_conflict_do_nothing(index_elements=[CommunityPool.name])
        )

        inserted = int(inserted_counts.get(name, 0))
        payload = {
            "probe_source": source,
            "source_query": source_query,
            "source_query_hash": q_hash,
            "evidence_score_sum": int(candidate_scores.get(name, 0)),
            "inserted_evidence_posts": inserted,
            "ts": now.isoformat(),
        }
        stmt = (
            pg_insert(DiscoveredCommunity)
            .values(
                name=name,
                discovered_from_keywords=payload,
                discovered_count=inserted,
                first_discovered_at=now,
                last_discovered_at=now,
                status="pending",
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=[DiscoveredCommunity.name],
                set_={
                    "discovered_count": DiscoveredCommunity.discovered_count + inserted,
                    "last_discovered_at": now,
                    "updated_at": now,
                },
            )
        )
        await session.execute(stmt)
        upserted += 1

        guess = warzone_by_sub.get(name)
        if guess is not None:
            try:
                warzone = str(getattr(guess, "warzone", "") or "")
                if warzone and warzone != "unknown":
                    tag = f"warzone:{warzone}"
                    payload2 = json.dumps(
                        {
                            "warzone_guess": warzone,
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

    return inserted_counts, upserted


async def execute_probe_workflow(
    *,
    workflow_input: ProbeWorkflowInput,
    deps: ProbeWorkflowDeps,
) -> ProbeWorkflowResult:
    plan = workflow_input.plan
    source = str(plan.meta.get("source") or "").strip().lower()
    if source not in {"search", "hot"}:
        raise ValueError("probe requires meta.source in {'search','hot'}")

    now = deps.now_provider()
    (
        posts_limit,
        max_candidate_subreddits,
        max_evidence_posts,
        max_evidence_per_subreddit,
        _max_posts_limit,
    ) = _coerce_probe_limits(plan=plan, source=source)

    min_score = int(plan.meta.get("min_score") or (100 if source == "hot" else 0))
    min_comments = int(plan.meta.get("min_comments") or (30 if source == "hot" else 0))
    max_age_hours = plan.meta.get("max_age_hours")
    if max_age_hours is None:
        max_age_hours = 72 if source == "hot" else 0
    max_age_hours = int(max_age_hours or 0)
    if max_age_hours > 0:
        max_age_hours = max(24, min(168, max_age_hours))

    fetched_posts, source_query = await _fetch_probe_posts(
        workflow_input=workflow_input,
        source=source,
        posts_limit=posts_limit,
    )
    unique_posts, per_sub_posts, scored_posts = _dedupe_and_score_posts(
        fetched_posts=fetched_posts,
        now=now,
        source=source,
        min_score=min_score,
        min_comments=min_comments,
        max_age_hours=max_age_hours,
        evidence_score_fn=deps.evidence_score_fn,
        spam_checker=deps.spam_checker,
    )

    truncated, picked_subs, top_posts, candidate_scores = _select_probe_candidates(
        source=source,
        scored_posts=scored_posts,
        per_sub_posts=per_sub_posts,
        max_candidate_subreddits=max_candidate_subreddits,
        max_evidence_posts=max_evidence_posts,
        max_evidence_per_subreddit=max_evidence_per_subreddit,
        evidence_score_fn=deps.evidence_score_fn,
    )

    q_hash = deps.query_hash_fn(source_query)
    inserted_counts, upserted = await _persist_probe_results(
        workflow_input=workflow_input,
        source=source,
        source_query=source_query,
        q_hash=q_hash,
        now=now,
        top_posts=top_posts,
        picked_subs=picked_subs,
        candidate_scores=candidate_scores,
        evidence_score_fn=deps.evidence_score_fn,
        warzone_config_path=deps.warzone_config_path,
    )
    return ProbeWorkflowResult(
        payload={
            "plan_kind": "probe",
            "source": source,
            "query": source_query,
            "status": "partial" if truncated else "completed",
            "reason": "caps_reached" if truncated else None,
            "evidence_posts_fetched": len(unique_posts),
            "evidence_posts_written": sum(inserted_counts.values()),
            "discovered_communities_upserted": upserted,
        }
    )


__all__ = [
    "ProbeWorkflowInput",
    "ProbeWorkflowDeps",
    "ProbeWorkflowResult",
    "execute_probe_workflow",
]
