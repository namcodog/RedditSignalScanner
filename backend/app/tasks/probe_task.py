from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml

from app.core.celery_app import celery_app
from app.db.session import SessionFactory
from app.services.crawl.plan_contract import (
    CrawlPlanContract,
    CrawlPlanLimits,
    compute_idempotency_key,
    compute_idempotency_key_human,
)
from app.services.crawl.crawler_run_targets_service import ensure_crawler_run_target
from app.services.crawl.crawler_runs_service import ensure_crawler_run
from app.services.infrastructure.task_outbox_service import enqueue_execute_target_outbox
from app.utils.asyncio_runner import run as run_coro

logger = logging.getLogger(__name__)

DEFAULT_PROBE_HOT_SOURCES: List[str] = [
    # Phase-1 hot anchors (Key 拍板)
    "r/shopify",
    "r/homeowners",
    "r/tools",
    "r/LocalLLaMA",
    "r/parenting",
    "r/coffee",
    "r/onebag",
    "r/frugal",
]

DEFAULT_PROBE_HOT_SOURCES_FILE = os.getenv(
    "PROBE_HOT_SOURCES_FILE", "config/probe_hot_sources.yaml"
)
DEFAULT_PROBE_HOT_SOURCES_PHASE = os.getenv("PROBE_HOT_SOURCES_PHASE", "phase1")


def _load_probe_hot_sources_default() -> list[object]:
    """
    Load default hot sources from a YAML config file (ops-friendly).

    Supports:
    - list[str]
    - list[dict{subreddit, sort?, time_filter?}]
    - dict with keys like {phase1: [...], phase2: [...]}
    """
    path = Path(DEFAULT_PROBE_HOT_SOURCES_FILE)
    if not path.exists():
        return list(DEFAULT_PROBE_HOT_SOURCES)

    try:
        with path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
    except Exception:
        logger.warning("Failed to load probe hot sources: %s", str(path))
        return list(DEFAULT_PROBE_HOT_SOURCES)

    raw: object = loaded
    if isinstance(loaded, dict):
        raw = loaded.get(DEFAULT_PROBE_HOT_SOURCES_PHASE) or loaded.get("phase1") or []

    if isinstance(raw, list):
        return list(raw)

    return list(DEFAULT_PROBE_HOT_SOURCES)


def _query_hash_short(query: str) -> str:
    raw = query.strip().encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


async def _plan_probe_search_target_impl(
    *,
    query: str,
    posts_limit: int = 50,
    time_filter: str = "week",
    sort: str = "relevance",
    max_evidence_posts: int = 50,
    max_discovered_communities: int = 50,
    reason: str = "user_query",
) -> Dict[str, Any]:
    """
    Probe Planner（search）：只下单，不执行。

    - 产出 crawler_run_targets(plan_kind=probe, meta.source=search)
    - 执行统一走 tasks.crawler.execute_target(target_id)，并路由到 probe_queue
    """
    crawl_run_id = str(uuid.uuid4())

    posts_limit = max(1, min(100, int(posts_limit)))
    max_evidence_posts = max(1, min(posts_limit, int(max_evidence_posts)))
    max_discovered_communities = max(1, min(200, int(max_discovered_communities)))

    plan = CrawlPlanContract(
        plan_kind="probe",
        target_type="query",
        target_value=query.strip(),
        reason=reason,
        limits=CrawlPlanLimits(posts_limit=posts_limit),
        meta={
            "source": "search",
            "time_filter": str(time_filter),
            "sort": str(sort),
            "queue": "probe_queue",
            "max_evidence_posts": max_evidence_posts,
            "max_discovered_communities": max_discovered_communities,
        },
    )
    idempotency_key = compute_idempotency_key(plan)
    idempotency_key_human = compute_idempotency_key_human(plan)
    target_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"crawler_run_target:{crawl_run_id}:{idempotency_key}")
    )

    # crawler_run_targets.subreddit 字段历史包袱较重；probe 用一个可读占位符便于排查
    subreddit_placeholder = f"probe_query:{_query_hash_short(query)}"

    async with SessionFactory() as session:
        await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
        await ensure_crawler_run(
            session,
            crawl_run_id=crawl_run_id,
            config={"mode": "probe_search", "query": query.strip()},
        )
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit=subreddit_placeholder,
            status="queued",
            plan_kind=plan.plan_kind,
            idempotency_key=idempotency_key,
            idempotency_key_human=idempotency_key_human,
            config=plan.model_dump(mode="json"),
        )
        await enqueue_execute_target_outbox(
            session,
            target_id=target_id,
            queue="probe_queue",
        )
        await session.commit()

    return {
        "crawl_run_id": crawl_run_id,
        "target_id": target_id,
        "plan_kind": "probe",
        "source": "search",
        "idempotency_key": idempotency_key,
        "idempotency_key_human": idempotency_key_human,
    }


@celery_app.task(name="tasks.probe.run_search_probe")  # type: ignore[misc]
def run_search_probe(
    *,
    query: str,
    posts_limit: int = 50,
    time_filter: str = "week",
    sort: str = "relevance",
    max_evidence_posts: int = 50,
    max_discovered_communities: int = 50,
    reason: str = "user_query",
) -> Dict[str, Any]:
    logger.info("Probe search (planner): query=%s limit=%s", query, posts_limit)
    return run_coro(
        _plan_probe_search_target_impl(
            query=query,
            posts_limit=posts_limit,
            time_filter=time_filter,
            sort=sort,
            max_evidence_posts=max_evidence_posts,
            max_discovered_communities=max_discovered_communities,
            reason=reason,
        )
    )

async def _plan_probe_hot_target_impl(
    *,
    hot_sources: list[object] | None = None,
    posts_per_source: int = 25,
    max_candidate_subreddits: int = 30,
    max_evidence_per_subreddit: int = 3,
    min_score: int = 100,
    min_comments: int = 30,
    max_age_hours: int = 72,
    reason: str = "hot_probe",
) -> Dict[str, Any]:
    """
    Probe Planner（hot）：只下单，不执行。

    - 产出单个 crawler_run_targets(plan_kind=probe, meta.source=hot, meta.hot_sources=[...])
    - 执行统一走 tasks.crawler.execute_target(target_id)，并路由到 probe_queue
    """
    crawl_run_id = str(uuid.uuid4())

    raw_sources = hot_sources if hot_sources is not None else _load_probe_hot_sources_default()
    # Hard clamps (planner-side guardrails)
    max_sources = int(os.getenv("PROBE_HOT_MAX_SOURCES", "20"))
    sources: list[object] = []
    for item in raw_sources:
        if len(sources) >= max(1, max_sources):
            break
        if isinstance(item, str):
            value = item.strip()
            if value:
                sources.append(value)
            continue
        if isinstance(item, dict):
            sub = str(item.get("subreddit") or "").strip()
            if not sub:
                continue
            sources.append(
                {
                    "subreddit": sub,
                    "sort": str(item.get("sort") or "hot"),
                    "time_filter": str(item.get("time_filter") or "day"),
                }
            )

    posts_per_source = max(1, min(50, int(posts_per_source)))
    max_candidate_subreddits = max(1, min(100, int(max_candidate_subreddits)))
    max_evidence_per_subreddit = max(1, min(5, int(max_evidence_per_subreddit)))
    min_score = max(0, int(min_score))
    min_comments = max(0, int(min_comments))
    max_age_hours = max(24, min(168, int(max_age_hours)))

    plan = CrawlPlanContract(
        plan_kind="probe",
        target_type="subreddit",
        target_value="r/probe_hot",
        reason=reason,
        limits=CrawlPlanLimits(posts_limit=posts_per_source),
        meta={
            "source": "hot",
            "queue": "probe_queue",
            "hot_sources": sources,
            "posts_per_source": posts_per_source,
            "max_candidate_subreddits": max_candidate_subreddits,
            "max_evidence_per_subreddit": max_evidence_per_subreddit,
            "min_score": min_score,
            "min_comments": min_comments,
            "max_age_hours": max_age_hours,
        },
    )
    idempotency_key = compute_idempotency_key(plan)
    idempotency_key_human = (
        f"probe_hot|sources={len(sources)}|posts_per_source={posts_per_source}"
    )
    target_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"crawler_run_target:{crawl_run_id}:{idempotency_key}")
    )

    async with SessionFactory() as session:
        await session.connection(execution_options={"isolation_level": "AUTOCOMMIT"})
        await ensure_crawler_run(
            session,
            crawl_run_id=crawl_run_id,
            config={
                "mode": "probe_hot",
                "sources": sources,
                "posts_per_source": posts_per_source,
            },
        )
        await ensure_crawler_run_target(
            session,
            community_run_id=target_id,
            crawl_run_id=crawl_run_id,
            subreddit="probe_hot",
            status="queued",
            plan_kind=plan.plan_kind,
            idempotency_key=idempotency_key,
            idempotency_key_human=idempotency_key_human,
            config=plan.model_dump(mode="json"),
        )
        await enqueue_execute_target_outbox(
            session,
            target_id=target_id,
            queue="probe_queue",
        )
        await session.commit()

    return {
        "crawl_run_id": crawl_run_id,
        "target_id": target_id,
        "plan_kind": "probe",
        "source": "hot",
        "idempotency_key": idempotency_key,
        "idempotency_key_human": idempotency_key_human,
        "sources": sources,
    }


@celery_app.task(name="tasks.probe.run_hot_probe")  # type: ignore[misc]
def run_hot_probe(
    *,
    hot_sources: list[object] | None = None,
    posts_per_source: int = 25,
    max_candidate_subreddits: int = 30,
    max_evidence_per_subreddit: int = 3,
    min_score: int = 100,
    min_comments: int = 30,
    max_age_hours: int = 72,
    reason: str = "hot_probe",
) -> Dict[str, Any]:
    logger.info(
        "Probe hot (planner): sources=%s posts_per_source=%s",
        len(hot_sources or DEFAULT_PROBE_HOT_SOURCES),
        posts_per_source,
    )
    return run_coro(
        _plan_probe_hot_target_impl(
            hot_sources=hot_sources,
            posts_per_source=posts_per_source,
            max_candidate_subreddits=max_candidate_subreddits,
            max_evidence_per_subreddit=max_evidence_per_subreddit,
            min_score=min_score,
            min_comments=min_comments,
            max_age_hours=max_age_hours,
            reason=reason,
        )
    )


__all__ = ["run_search_probe", "run_hot_probe"]
