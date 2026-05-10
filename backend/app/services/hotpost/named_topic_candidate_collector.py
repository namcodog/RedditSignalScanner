from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.core.config import settings
from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_signal import SourceScopeId
from app.schemas.hotpost_source_scopes import RedditSearchSpec
from app.services.hotpost.candidate_spec_collector import collect_candidates_for_spec
from app.services.hotpost.card_candidate_store import upsert_candidate
from app.services.hotpost.hotpost_supply_contract import get_supply_collect_profile
from app.services.hotpost.named_topic_watchlist import NamedTopicWatch
from app.services.infrastructure.reddit_collect_client import build_collect_reddit_client


async def collect_named_topic_candidates(
    watches: list[NamedTopicWatch],
    *,
    mode: str = "safe",
    persist: bool = True,
    enrich_comments: bool = True,
) -> list[CandidatePack]:
    if not watches:
        return []
    collect_defaults = get_supply_collect_profile(mode)
    comment_timeout = int(collect_defaults.get("comment_request_timeout") or 8)
    collected_at = datetime.now(timezone.utc)
    collect_batch_id = f"named-topics-{collected_at.strftime('%Y%m%d%H%M%S')}"
    comment_cache:Optional[ dict[str, list[dict]]] = {}
    comment_tasks: dict[str, asyncio.Task[list[dict]]] = {}
    imported: dict[str, CandidatePack] = {}
    async with build_collect_reddit_client(
        request_timeout=20.0,
        search_timeout=12.0,
        max_concurrency=max(1, collect_defaults["api_max_concurrency"]),
        low_quota_remaining_threshold=int(collect_defaults.get("low_quota_remaining_threshold") or 12),
        low_quota_cooldown_seconds=float(collect_defaults.get("low_quota_cooldown_seconds") or 20),
        stop_comment_fetch_below_remaining=int(collect_defaults.get("stop_comment_fetch_below_remaining") or 18),
        max_consecutive_rate_limit_errors=int(collect_defaults.get("max_consecutive_rate_limit_errors") or 3),
    ) as reddit:
        for watch in watches:
            watch_ids: set[str] = set()
            for subreddit in watch.subreddits:
                for query in watch.queries:
                    if len(watch_ids) >= watch.candidate_cap:
                        break
                    spec = _build_named_topic_spec(watch, subreddit=subreddit, query=query)
                    candidates = await collect_candidates_for_spec(
                        reddit,
                        watch.scope_id,
                        spec,
                        collect_batch_id=collect_batch_id,
                        collected_at=collected_at,
                        comment_timeout=comment_timeout,
                        comment_cache=comment_cache,
                        comment_tasks=comment_tasks,
                        enrich_comments=enrich_comments,
                    )
                    for candidate in candidates:
                        imported[candidate.candidate_id] = candidate
                        watch_ids.add(candidate.candidate_id)
                        if len(watch_ids) >= watch.candidate_cap:
                            break
                if len(watch_ids) >= watch.candidate_cap:
                    break
    items = sorted(imported.values(), key=lambda item: item.collected_at, reverse=True)
    if persist:
        for item in items:
            upsert_candidate(item)
    return items


def build_custom_named_topic_watch(
    *,
    topic_id: str,
    scope_id: SourceScopeId,
    topic_pack_id: str,
    topic_cluster_ids:Optional[ list[str]] = None,
    queries: list[str],
    subreddits: list[str],
    time_filter: str = "week",
    candidate_cap: int = 4,
) -> NamedTopicWatch:
    if not queries:
        raise ValueError("queries cannot be empty")
    if not subreddits:
        raise ValueError("subreddits cannot be empty")
    return NamedTopicWatch(
        topic_id=topic_id,
        scope_id=scope_id,
        topic_pack_id=topic_pack_id,
        topic_cluster_ids=tuple(dict.fromkeys(item.strip() for item in (topic_cluster_ids or []) if item.strip())),
        queries=tuple(dict.fromkeys(item.strip() for item in queries if item.strip())),
        subreddits=tuple(dict.fromkeys(item.strip().replace("r/", "") for item in subreddits if item.strip())),
        time_filter=time_filter,
        candidate_cap=max(1, candidate_cap),
    )


def _build_named_topic_spec(watch: NamedTopicWatch, *, subreddit: str, query: str) -> RedditSearchSpec:
    return RedditSearchSpec(
        source_scope_id=watch.scope_id,
        topic_pack_id=watch.topic_pack_id,
        topic_cluster_id=watch.topic_cluster_ids[0] if len(watch.topic_cluster_ids) == 1 else None,
        topic_cluster_ids=list(watch.topic_cluster_ids),
        named_topic_ids=[watch.topic_id],
        subreddit=subreddit,
        mode="search",
        sort="relevance",
        time_filter=watch.time_filter,
        query=query,
        listing_source=f"named-topic-search:relevance:{watch.time_filter}",
        primary_reason=f"{watch.topic_pack_id}:named_topic",
        matched_keywords=[watch.topic_id],
    )


__all__ = ["build_custom_named_topic_watch", "collect_named_topic_candidates"]
