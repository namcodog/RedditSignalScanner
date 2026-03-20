from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.services.hotpost.hotpost_deps_factory import (
    HotpostSearchDepsFactoryInput,
    build_hotpost_search_deps,
)


async def _noop_async(*_args: Any, **_kwargs: Any) -> Any:
    return None


@pytest.mark.asyncio
async def test_build_hotpost_search_deps_wraps_query_and_repository_calls() -> None:
    db = object()
    redis_client = object()
    llm_client = object()
    resolve_calls: list[tuple[Any, Any]] = []
    create_calls: list[tuple[Any, dict[str, Any]]] = []
    update_calls: list[tuple[Any, dict[str, Any]]] = []

    async def _resolve_query(query: str, *, redis_client: Any, llm_client: Any) -> Any:
        resolve_calls.append((redis_client, llm_client))
        return SimpleNamespace(search_query=query)

    async def _create_hotpost_query(db_arg: Any, **kwargs: Any) -> None:
        create_calls.append((db_arg, kwargs))

    async def _update_hotpost_query(db_arg: Any, **kwargs: Any) -> None:
        update_calls.append((db_arg, kwargs))

    deps = build_hotpost_search_deps(
        HotpostSearchDepsFactoryInput(
            db=db,
            redis_client=redis_client,
            lexicon=object(),
            reddit_client=SimpleNamespace(
                search_subreddits=_noop_async,
                search_posts=_noop_async,
            ),
            llm_client=llm_client,
            getenv=lambda key, default: default,
            resolve_query=_resolve_query,
            create_hotpost_query=_create_hotpost_query,
            update_hotpost_query=_update_hotpost_query,
            collect_evidence=_noop_async,
            build_report_result=_noop_async,
            persist_side_effects=_noop_async,
            maybe_discover_community=_noop_async,
            upsert_evidence_post=_noop_async,
            insert_query_evidence_map=_noop_async,
            resolve_mode=lambda request: "trending",
            resolve_time_filter=lambda mode, request: "all",
            resolve_sort=lambda mode: "top",
            split_search_queries=lambda query, max_chars: [query[:max_chars]],
            acquire_rate_budget=_noop_async,
            search_subreddit_posts=_noop_async,
            fetch_comments=_noop_async,
            select_signals=lambda mode, text: {},
            sentiment_label=lambda mode, text, signals: "neutral",
            build_post=lambda *args, **kwargs: None,
            build_pain_points=lambda posts, categories: [],
            confidence_level=lambda evidence_count: "low",
            maybe_llm_summary=_noop_async,
        )
    )

    resolution = await deps.resolve_query("robot vacuum")
    await deps.create_hotpost_query(query_id="q1")
    await deps.update_hotpost_query(query_id="q1")

    assert resolution.search_query == "robot vacuum"
    assert resolve_calls == [(redis_client, llm_client)]
    assert create_calls == [(db, {"query_id": "q1"})]
    assert update_calls == [(db, {"query_id": "q1"})]
