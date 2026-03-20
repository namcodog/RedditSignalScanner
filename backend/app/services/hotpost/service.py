from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.services.infrastructure.global_rate_limiter import GlobalRateLimiter
from app.services.hotpost.keywords import HotpostLexicon, load_default_hotpost_keywords
from app.services.hotpost.cache import build_hotpost_cache_key, get_hotpost_cache_ttl_seconds
from app.services.hotpost.evidence_collection_workflow import collect_hotpost_evidence
from app.services.hotpost.hotpost_deps_factory import (
    HotpostSearchDepsFactoryInput,
    build_hotpost_debug_contract,
    build_hotpost_response_status,
    build_hotpost_search_deps,
)
from app.services.hotpost.hotpost_runtime import (
    acquire_hotpost_rate_budget,
    build_hotpost_fallback_text,
    build_hotpost_pain_points,
    build_hotpost_post,
    fetch_hotpost_comments,
    maybe_build_hotpost_llm_summary,
    resolve_hotpost_confidence_level,
    resolve_hotpost_mode,
    resolve_hotpost_sentiment_label,
    resolve_hotpost_sort,
    resolve_hotpost_time_filter,
    search_hotpost_subreddit_posts,
    select_hotpost_signals,
    split_hotpost_search_queries,
)
from app.services.hotpost.query_resolver import resolve_hotpost_query
from app.services.hotpost.persistence_workflow import persist_hotpost_search_side_effects
from app.services.hotpost.report_workflow import build_hotpost_report_result
from app.services.hotpost.search_workflow import (
    HotpostSearchWorkflowDeps,
    HotpostSearchWorkflowInput,
    run_hotpost_search_workflow,
)
from app.services.hotpost.repository import (
    create_hotpost_query,
    insert_query_evidence_map,
    maybe_discover_community,
    upsert_evidence_post,
    update_hotpost_query,
)
from app.services.hotpost.queue import HotpostQueueTracker
from app.services.llm.clients.openai_client import OpenAIChatClient, resolve_llm_api_key
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditPost
from app.schemas.hotpost import (
    Hotpost,
    HotpostDebugInfo,
    HotpostSearchRequest,
    HotpostSearchResponse,
    PainPoint,
)


DEFAULT_RATE_LIMIT = 100
DEFAULT_RATE_WINDOW = 600
COMMENTS_TTL_SECONDS = 2 * 60 * 60
logger = logging.getLogger(__name__)


class _NullRedditClient:
    async def search_subreddits(self, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        return []

    async def search_subreddit_page(self, *_args: Any, **_kwargs: Any) -> tuple[list[RedditPost], None]:
        return [], None

    async def search_posts(self, *_args: Any, **_kwargs: Any) -> list[RedditPost]:
        return []

    async def fetch_post_comments(self, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        return []

    async def close(self) -> None:
        return None


class HotpostService:
    def __init__(
        self,
        *,
        settings: Settings,
        db: AsyncSession,
        redis_client: Redis | None = None,
        lexicon: HotpostLexicon | None = None,
        reddit_client: RedditAPIClient | None = None,
    ) -> None:
        self._settings = settings
        self._db = db
        self._redis = redis_client or Redis.from_url(
            settings.reddit_cache_redis_url, decode_responses=True
        )
        self._lexicon = lexicon or load_default_hotpost_keywords()
        if reddit_client is not None:
            self._reddit = reddit_client
        elif settings.reddit_client_id and settings.reddit_client_secret:
            self._reddit = RedditAPIClient(
                settings.reddit_client_id,
                settings.reddit_client_secret,
                settings.reddit_user_agent,
                rate_limit=settings.reddit_rate_limit,
                rate_limit_window=settings.reddit_rate_limit_window_seconds,
                request_timeout=settings.reddit_request_timeout_seconds,
                max_concurrency=settings.reddit_max_concurrency,
            )
        elif settings.allow_mock_fallback or settings.environment.lower() == "test":
            self._reddit = _NullRedditClient()
        else:
            raise ValueError("REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET required for hotpost search")
        self._rate_limiter = GlobalRateLimiter(
            self._redis,
            limit=int(os.getenv("HOTPOST_RATE_LIMIT_MAX_REQUESTS", os.getenv("RATE_LIMIT_MAX_REQUESTS", DEFAULT_RATE_LIMIT))),
            window_seconds=int(os.getenv("HOTPOST_RATE_LIMIT_WINDOW_SECONDS", os.getenv("RATE_LIMIT_WINDOW_SECONDS", DEFAULT_RATE_WINDOW))),
            namespace="hotpost:qpm",
            client_id=settings.reddit_client_id or "default",
        )

    async def close(self) -> None:
        await self._reddit.close()

    def _resolve_mode(self, request: HotpostSearchRequest) -> str:
        return resolve_hotpost_mode(request)

    @staticmethod
    def _split_search_queries(search_query: str, *, max_chars: int) -> list[str]:
        return split_hotpost_search_queries(search_query, max_chars=max_chars)

    @staticmethod
    def _resolve_time_filter(mode: str, request: HotpostSearchRequest) -> str:
        return resolve_hotpost_time_filter(mode, request)

    def _resolve_sort(self, mode: str) -> str:
        return resolve_hotpost_sort(mode)

    async def _acquire_rate_budget(
        self,
        *,
        cost: int,
        queue_tracker: HotpostQueueTracker | None = None,
    ) -> None:
        await acquire_hotpost_rate_budget(
            cost=cost,
            rate_limiter=self._rate_limiter,
            queue_tracker=queue_tracker,
        )

    async def _search_subreddit_posts(
        self,
        subreddit: str,
        query: str,
        *,
        sort: str,
        time_filter: str,
        max_posts: int,
        queue_tracker: HotpostQueueTracker | None = None,
    ) -> tuple[list[RedditPost], int]:
        return await search_hotpost_subreddit_posts(
            subreddit,
            query,
            sort=sort,
            time_filter=time_filter,
            max_posts=max_posts,
            queue_tracker=queue_tracker,
            acquire_rate_budget=self._acquire_rate_budget,
            search_subreddit_page=self._reddit.search_subreddit_page,
        )

    async def _fetch_comments(
        self,
        post_id: str,
        *,
        queue_tracker: HotpostQueueTracker | None = None,
    ) -> list[dict[str, Any]]:
        return await fetch_hotpost_comments(
            post_id,
            queue_tracker=queue_tracker,
            acquire_rate_budget=self._acquire_rate_budget,
            fetch_post_comments=self._reddit.fetch_post_comments,
        )

    def _select_signals(self, mode: str, text: str) -> dict[str, list[str]]:
        return select_hotpost_signals(mode, text, lexicon=self._lexicon)

    def _sentiment_label(self, mode: str, text: str, signals: dict[str, list[str]]) -> str:
        return resolve_hotpost_sentiment_label(
            mode,
            text,
            signals,
            lexicon=self._lexicon,
        )

    def _build_post(self, post: RedditPost, *, rank: int, signals: dict[str, list[str]]) -> Hotpost:
        return build_hotpost_post(post, rank=rank, signals=signals)

    def _build_pain_points(self, posts: list[Hotpost], categories: list[str]) -> list[PainPoint]:
        return build_hotpost_pain_points(posts, categories)

    def _confidence_level(self, evidence_count: int) -> str:
        return resolve_hotpost_confidence_level(evidence_count)

    @staticmethod
    def _resolve_response_status(
        *,
        resolution_reason: str | None,
        summary_result: HotpostSummaryResult,
        report_result: HotpostLLMReportResult,
    ) -> tuple[str, list[str]]:
        return build_hotpost_response_status(
            resolution_reason=resolution_reason,
            summary_result=summary_result,
            report_result=report_result,
        )

    @staticmethod
    def _build_debug_info(
        *,
        resolution_source: str,
        resolution_reason: str | None,
        search_query: str,
        query_parts: list[str],
        keywords: list[str],
        time_filter: str,
        sort: str,
        subreddits: list[str] | None,
        raw_posts: int,
        filtered_posts: int,
        relevance_filtered: int,
        summary_result: HotpostSummaryResult,
        report_result: HotpostLLMReportResult,
        degraded_reasons: list[str],
        response_source: str,
    ) -> HotpostDebugInfo:
        return build_hotpost_debug_contract(
            resolution_source=resolution_source,
            resolution_reason=resolution_reason,
            search_query=search_query,
            query_parts=query_parts,
            keywords=keywords,
            time_filter=time_filter,
            sort=sort,
            subreddits=subreddits,
            raw_posts=raw_posts,
            filtered_posts=filtered_posts,
            relevance_filtered=relevance_filtered,
            summary_result=summary_result,
            report_result=report_result,
            degraded_reasons=degraded_reasons,
            response_source=response_source,
        )

    async def _maybe_llm_summary(
        self,
        *,
        query: str,
        posts: list[Hotpost],
        confidence: str,
        sentiment_overview: dict[str, float] | None = None,
        community_distribution: dict[str, str] | None = None,
    ) -> HotpostSummaryResult:
        return await maybe_build_hotpost_llm_summary(
            query=query,
            posts=posts,
            confidence=confidence,
            sentiment_overview=sentiment_overview,
            community_distribution=community_distribution,
            llm_model_name=self._settings.llm_model_name,
        )

    @staticmethod
    def _fallback_summary(
        posts: list[Hotpost],
        *,
        sentiment_overview: dict[str, float] | None = None,
        community_distribution: dict[str, str] | None = None,
    ) -> str:
        return build_hotpost_fallback_text(
            posts,
            sentiment_overview=sentiment_overview,
            community_distribution=community_distribution,
        )

    async def search(
        self,
        request: HotpostSearchRequest,
        *,
        user_id: uuid.UUID | None = None,
        session_id: str | None = None,
        ip_hash: str | None = None,
    ) -> HotpostSearchResponse:
        llm_client = None
        enable_translation = os.getenv("ENABLE_HOTPOST_QUERY_TRANSLATION", "true").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        if enable_translation and resolve_llm_api_key():
            llm_client = OpenAIChatClient(model=self._settings.llm_model_name)
        result = await run_hotpost_search_workflow(
            workflow_input=HotpostSearchWorkflowInput(
                request=request,
                user_id=user_id,
                session_id=session_id,
                ip_hash=ip_hash,
                llm_model_name=self._settings.llm_model_name,
                comments_ttl_seconds=COMMENTS_TTL_SECONDS,
            ),
            deps=self._search_workflow_deps(llm_client=llm_client),
        )
        return result.response

    def _search_workflow_deps(
        self,
        *,
        llm_client: Any | None,
    ) -> HotpostSearchWorkflowDeps:
        return build_hotpost_search_deps(
            HotpostSearchDepsFactoryInput(
                db=self._db,
                redis_client=self._redis,
                lexicon=self._lexicon,
                reddit_client=self._reddit,
                llm_client=llm_client,
                getenv=os.getenv,
                resolve_query=resolve_hotpost_query,
                create_hotpost_query=create_hotpost_query,
                update_hotpost_query=update_hotpost_query,
                collect_evidence=collect_hotpost_evidence,
                build_report_result=build_hotpost_report_result,
                persist_side_effects=persist_hotpost_search_side_effects,
                maybe_discover_community=maybe_discover_community,
                upsert_evidence_post=upsert_evidence_post,
                insert_query_evidence_map=insert_query_evidence_map,
                tracker_factory=HotpostQueueTracker,
                resolve_mode=self._resolve_mode,
                resolve_time_filter=self._resolve_time_filter,
                resolve_sort=self._resolve_sort,
                split_search_queries=self._split_search_queries,
                acquire_rate_budget=self._acquire_rate_budget,
                search_subreddit_posts=self._search_subreddit_posts,
                fetch_comments=self._fetch_comments,
                select_signals=self._select_signals,
                sentiment_label=self._sentiment_label,
                build_post=self._build_post,
                build_pain_points=self._build_pain_points,
                confidence_level=self._confidence_level,
                maybe_llm_summary=self._maybe_llm_summary,
            )
        )


__all__ = ["HotpostService"]
