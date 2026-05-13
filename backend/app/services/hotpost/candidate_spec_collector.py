from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional, Any, cast

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_signal import SourceScopeId
from app.services.hotpost.hotpost_supply_contract import load_hotpost_supply_contract
from app.services.hotpost.hotpost_supply_projection import get_topic_pack_payload
from app.services.hotpost.reddit_candidate_mapper import build_candidate_pack
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditAPIError


logger = logging.getLogger(__name__)


async def collect_candidates_for_spec(
    reddit: RedditAPIClient,
    scope_id: SourceScopeId,
    spec: Any,
    *,
    collect_batch_id: str,
    collected_at: datetime,
    comment_timeout: int,
    comment_cache:Optional[ dict[str, list[dict]]],
    comment_tasks: dict[str, asyncio.Task[list[dict]]],
    enrich_comments: bool = True,
    selected_post_ids: set[str] | None = None,
    prefer_fallback_for_posts: bool = False,
) -> list[CandidatePack]:
    try:
        posts = await fetch_posts_for_spec(
            reddit,
            spec,
            prefer_fallback_for_posts=prefer_fallback_for_posts,
        )
    except RedditAPIError as exc:
        logger.warning(
            "collect_candidates_for_spec skipped spec after reddit failure: scope=%s pack=%s subreddit=%s mode=%s query=%s error=%s",
            scope_id,
            spec.topic_pack_id,
            spec.subreddit,
            spec.mode,
            spec.query,
            exc,
        )
        return []
    filtered_posts = [post for post in posts if not _is_noise_post(scope_id, post, spec.topic_pack_id)]
    if selected_post_ids is not None:
        filtered_posts = [post for post in filtered_posts if post.id in selected_post_ids]
    selected_posts = filtered_posts[:pack_candidate_cap(scope_id, spec.topic_pack_id)]
    if not selected_posts:
        return []
    if not enrich_comments:
        return [
            candidate
            for candidate in (
                build_candidate_pack(
                    spec,
                    post,
                    [],
                    collect_batch_id=collect_batch_id,
                    collected_at=collected_at,
                )
                for post in selected_posts
            )
            if candidate is not None
        ]
    pending_tasks: list[asyncio.Task[list[dict]]] = []
    if hasattr(reddit, "should_skip_comment_fetch") and reddit.should_skip_comment_fetch():
        logger.warning(
            "collect_candidates_for_spec skipped comment enrichment due to low Reddit quota: scope=%s pack=%s subreddit=%s snapshot=%s",
            scope_id,
            spec.topic_pack_id,
            spec.subreddit,
            getattr(reddit, "get_ratelimit_snapshot", lambda: {})(),
        )
        return [
            candidate
            for candidate in (
                build_candidate_pack(
                    spec,
                    post,
                    [],
                    collect_batch_id=collect_batch_id,
                    collected_at=collected_at,
                )
                for post in selected_posts
            )
            if candidate is not None
        ]
    for post in selected_posts:
        if post.id in comment_cache:
            continue
        task = comment_tasks.get(post.id)
        if task is None:
            task = asyncio.create_task(
                reddit.fetch_post_comments(
                    post.id,
                    sort="top",
                    depth=1,
                    limit=pack_comments_fetch_limit(scope_id, spec.topic_pack_id),
                    mode="topn",
                    comment_timeout=float(comment_timeout),
                )
            )
            comment_tasks[post.id] = task
        pending_tasks.append(task)
    if pending_tasks:
        await _await_comment_tasks(
            pending_tasks,
            timeout_seconds=_comment_batch_timeout_seconds(reddit, comment_timeout=float(comment_timeout)),
            log_context={
                "scope_id": scope_id,
                "topic_pack_id": spec.topic_pack_id,
                "subreddit": spec.subreddit,
                "phase": "candidate_enrich",
            },
        )
    for post in selected_posts:
        if post.id in comment_cache:
            continue
        task = comment_tasks.pop(post.id, None)
        if task is None:
            continue
        comment_cache[post.id] = _task_comments_or_empty(
            task,
            log_context={
                "scope_id": scope_id,
                "topic_pack_id": spec.topic_pack_id,
                "subreddit": spec.subreddit,
                "phase": "candidate_enrich",
                "post_id": post.id,
            },
        )
    candidates: list[CandidatePack] = []
    for post in selected_posts:
        comments = comment_cache.get(post.id) or []
        candidate = build_candidate_pack(
            spec,
            post,
            comments,
            collect_batch_id=collect_batch_id,
            collected_at=collected_at,
        )
        if candidate is not None:
            candidates.append(candidate)
    return candidates


async def fetch_posts_for_spec(
    reddit: RedditAPIClient,
    spec: Any,
    *,
    prefer_fallback_for_posts: bool = False,
) -> list[Any]:
    fetch_limit = pack_fetch_limit(spec.source_scope_id, spec.topic_pack_id, spec.mode)
    if spec.mode == "search" and spec.query:
        try:
            posts, _ = await reddit.search_subreddit_page(
                spec.subreddit,
                spec.query,
                limit=fetch_limit,
                sort="relevance",
                time_filter=spec.time_filter,
                restrict_sr=1,
                syntax=None,
                prefer_fallback=prefer_fallback_for_posts,
            )
        except TypeError:
            posts, _ = await reddit.search_subreddit_page(
                spec.subreddit,
                spec.query,
                limit=fetch_limit,
                sort="relevance",
                time_filter=spec.time_filter,
                restrict_sr=1,
                syntax=None,
            )
        return posts
    try:
        posts, _ = await reddit.fetch_subreddit_posts(
            spec.subreddit,
            limit=fetch_limit,
            time_filter=spec.time_filter,
            sort=spec.sort,
            prefer_fallback=prefer_fallback_for_posts,
        )
    except TypeError:
        posts, _ = await reddit.fetch_subreddit_posts(
            spec.subreddit,
            limit=fetch_limit,
            time_filter=spec.time_filter,
            sort=spec.sort,
        )
    return posts


def pack_candidate_cap(scope_id: SourceScopeId | str, topic_pack_id:Optional[ str] = None) -> int:
    resolved_scope_id, resolved_pack_id = _resolve_scope_and_pack(scope_id, topic_pack_id)
    if not resolved_pack_id:
        return 2
    return int(get_topic_pack_payload(resolved_scope_id, resolved_pack_id)["candidate_cap"])


def pack_fetch_limit(scope_id: SourceScopeId | str, topic_pack_id:Optional[ str], mode: str) -> int:
    resolved_scope_id, resolved_pack_id = _resolve_scope_and_pack(scope_id, topic_pack_id)
    if not resolved_pack_id:
        return 12
    payload = get_topic_pack_payload(resolved_scope_id, resolved_pack_id)
    key = "search_fetch_limit" if mode == "search" else "listing_fetch_limit"
    return int(payload[key])


def pack_comments_fetch_limit(scope_id: SourceScopeId | str, topic_pack_id:Optional[ str]) -> int:
    resolved_scope_id, resolved_pack_id = _resolve_scope_and_pack(scope_id, topic_pack_id)
    if not resolved_pack_id:
        return 8
    return int(get_topic_pack_payload(resolved_scope_id, resolved_pack_id)["comments_fetch_limit"])


def _resolve_scope_and_pack(scope_or_pack: SourceScopeId | str, topic_pack_id:Optional[ str]) ->Optional[ tuple[SourceScopeId, str]]:
    if topic_pack_id is not None:
        return cast(SourceScopeId, scope_or_pack), topic_pack_id
    contract = load_hotpost_supply_contract()
    for scope_id, scope in contract["scopes"].items():
        if scope_or_pack in scope["topic_packs"]:
            return cast(SourceScopeId, scope_id), cast(str, scope_or_pack)
    raise KeyError(f"Unknown topic pack: {scope_or_pack}")


def _is_noise_post(scope_id: SourceScopeId, post: Any, topic_pack_id:Optional[ str]) -> bool:
    normalized = f"{getattr(post, 'title', '')} {getattr(post, 'selftext', '')}".lower()
    if scope_id == "business-growth-ops":
        blocked = ["hiring", "looking for agency", "job opening", "webinar"]
        if topic_pack_id != "organic-discovery":
            blocked.append("newsletter")
        return any(term in normalized for term in blocked)
    if scope_id == "ecommerce-sellers" and topic_pack_id == "selection-signals":
        blocked = ["dropshipping", "amazon fba course", "promo code", "black friday sale", "coupon"]
        return any(term in normalized for term in blocked)
    return False


def _comment_batch_timeout_seconds(reddit: Any, *, comment_timeout: float) -> float:
    primary_timeout = max(1.0, float(comment_timeout))
    base_timeout = max(4.0, primary_timeout + 4.0)
    fallback = getattr(reddit, "fallback", None)
    if fallback is None:
        return base_timeout
    fallback_timeout = getattr(fallback, "request_timeout", None)
    try:
        fallback_seconds = float(fallback_timeout)
    except (TypeError, ValueError):
        fallback_seconds = max(10.0, primary_timeout)
    return max(base_timeout, primary_timeout + fallback_seconds + 4.0)


async def _await_comment_tasks(
    tasks: list[asyncio.Task[list[dict]]],
    *,
    timeout_seconds: float,
    log_context: dict[str, Any],
) -> None:
    if not tasks:
        return
    try:
        await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "comment enrichment batch timed out: phase=%s scope=%s pack=%s subreddit=%s timeout=%.1fs pending=%s",
            log_context.get("phase"),
            log_context.get("scope_id"),
            log_context.get("topic_pack_id"),
            log_context.get("subreddit"),
            timeout_seconds,
            sum(1 for task in tasks if not task.done()),
        )
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def _task_comments_or_empty(task: asyncio.Task[list[dict]], *, log_context: dict[str, Any]) -> list[dict]:
    if task.cancelled():
        return []
    try:
        result = task.result()
    except Exception as exc:  # pragma: no cover - exercised via caller tests
        logger.warning(
            "comment enrichment task failed: phase=%s scope=%s pack=%s subreddit=%s post_id=%s error=%s",
            log_context.get("phase"),
            log_context.get("scope_id"),
            log_context.get("topic_pack_id"),
            log_context.get("subreddit"),
            log_context.get("post_id"),
            exc,
        )
        return []
    return result if isinstance(result, list) else []


__all__ = [
    "collect_candidates_for_spec",
    "fetch_posts_for_spec",
    "pack_candidate_cap",
    "pack_comments_fetch_limit",
    "pack_fetch_limit",
]
