from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_source_scopes import RedditSearchSpec


def _post(post_id: str, title: str, subreddit: str = "AmazonSeller") -> SimpleNamespace:
    return SimpleNamespace(
        id=post_id,
        subreddit=subreddit,
        title=title,
        selftext="body",
        score=100,
        num_comments=20,
        created_utc=1_775_200_000,
        permalink=f"/r/{subreddit}/comments/{post_id}/test",
    )


def _candidate(
    spec: RedditSearchSpec,
    *,
    candidate_id: str,
    post_id: str,
    title: str,
    subreddit: str | None = None,
    quote_count: int = 1,
) -> CandidatePack:
    return CandidatePack.model_validate(
        {
            "candidate_id": candidate_id,
            "signal_id": f"sig-{candidate_id}",
            "source_scope_id": spec.source_scope_id,
            "source_scope_name": {
                "ai-automation": "AI 与自动化",
                "business-growth-ops": "商业增长与运营",
                "ecommerce-sellers": "电商与卖家",
            }[spec.source_scope_id],
            "topic_pack_id": spec.topic_pack_id,
            "topic_cluster_id": spec.topic_cluster_id,
            "topic_cluster_ids": list(spec.topic_cluster_ids or ([] if not spec.topic_cluster_id else [spec.topic_cluster_id])),
            "query": spec.query or spec.listing_source or "listing:hot:day",
            "matched_subreddit": subreddit or spec.subreddit,
            "post_id": post_id,
            "title": title,
            "score": 100,
            "num_comments": 20,
            "created_at": "2026-04-09T00:00:00Z",
            "collected_at": "2026-04-09T00:00:00Z",
            "collect_batch_id": "batch-1",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "new_threads_24h",
            "listing_source": spec.listing_source,
            "primary_reason": spec.primary_reason,
            "matched_keywords": spec.matched_keywords or ([spec.query] if spec.query else []),
            "top_communities": [f"r/{subreddit or spec.subreddit}"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": quote_count,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": (
                [
                    {
                        "text": "useful quote",
                        "community": f"r/{subreddit or spec.subreddit}",
                        "permalink": f"/r/{subreddit or spec.subreddit}/comments/{post_id}/c1",
                    }
                ]
                if quote_count
                else []
            ),
        }
    )


class _FakeReddit:
    def __init__(self, *args, **kwargs) -> None:
        self.kwargs = kwargs
        self.comment_calls: list[str] = []
        self._stats = {
            "primary_post_requests": 0,
            "fallback_post_requests": 0,
            "primary_comment_requests": 0,
            "fallback_comment_requests": 0,
            "discover_assist_hits": 0,
            "comment_assist_hits": 0,
            "rescue_hits": 0,
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def fetch_post_comments(self, post_id: str, **kwargs):
        self.comment_calls.append(post_id)
        self._stats["primary_comment_requests"] += 1
        return [
            {
                "body": "This is a useful quote with enough detail.",
                "score": 12,
                "author": "u",
                "permalink": f"/r/test/comments/{post_id}/c1",
            }
        ]

    def get_collect_stats(self) -> dict[str, int]:
        return dict(self._stats)


def _spec(
    *,
    scope_id: str,
    topic_pack_id: str,
    subreddit: str,
    query: str | None = None,
    mode: str = "search",
    primary_reason: str | None = None,
    matched_keywords: list[str] | None = None,
    topic_cluster_id: str | None = None,
    topic_cluster_ids: list[str] | None = None,
) -> RedditSearchSpec:
    return RedditSearchSpec(
        source_scope_id=scope_id,
        topic_pack_id=topic_pack_id,
        topic_cluster_id=topic_cluster_id,
        topic_cluster_ids=topic_cluster_ids or ([topic_cluster_id] if topic_cluster_id else []),
        subreddit=subreddit,
        mode=mode,
        sort="relevance" if mode == "search" else "hot",
        time_filter="week" if mode == "search" else "day",
        query=query,
        listing_source="search:relevance:week" if mode == "search" else "listing:hot:day",
        primary_reason=primary_reason or f"{topic_pack_id}:reason",
        matched_keywords=matched_keywords or ([query] if query else []),
    )


@pytest.mark.asyncio
async def test_collect_scope_candidates_keeps_nonempty_spec_results(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    spec = _spec(
        scope_id="ecommerce-sellers",
        topic_pack_id="category-winds",
        subreddit="AmazonSeller",
        query="what niche still has room",
        primary_reason="category-winds:change_keyword",
    )

    async def _fake_collect(reddit, scope_id, spec, **kwargs):
        return [_candidate(spec, candidate_id="cand-category-real-1", post_id="real-1", title="What niche still has room?")]

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: [spec])
    monkeypatch.setattr(collector, "build_topic_pack_candidate_quotas", lambda scope_id, max_candidates: {"category-winds": 1})
    monkeypatch.setattr(collector, "collect_candidates_for_spec", _fake_collect)
    monkeypatch.setattr(
        collector,
        "build_collect_reddit_client",
        lambda **kwargs: _FakeReddit(**kwargs),
    )
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)

    items = await collector.collect_scope_candidates("ecommerce-sellers", max_candidates=4)
    assert len(items) == 1
    assert items[0].post_id == "real-1"


@pytest.mark.asyncio
async def test_collect_scope_candidates_batches_specs_concurrently(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    specs = [
        _spec(
            scope_id="business-growth-ops",
            topic_pack_id="organic-discovery",
            subreddit=subreddit,
            query=f"query-{idx}",
            primary_reason="organic-discovery:problem_keyword",
        )
        for idx, subreddit in enumerate(["SEO", "TechSEO", "bigseo"])
    ]

    async def _fake_collect(reddit, scope_id, spec, **kwargs):
        await asyncio.sleep(0.05)
        return [_candidate(spec, candidate_id=f"cand-{spec.subreddit}", post_id=spec.query or "post", title=f"title-{spec.query}")]

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: specs)
    monkeypatch.setattr(collector, "build_topic_pack_candidate_quotas", lambda scope_id, max_candidates: {"organic-discovery": 3})
    monkeypatch.setattr(collector, "collect_candidates_for_spec", _fake_collect)
    monkeypatch.setattr(
        collector,
        "build_collect_reddit_client",
        lambda **kwargs: _FakeReddit(**kwargs),
    )
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)
    monkeypatch.setattr(
        collector,
        "get_supply_collect_profile",
        lambda mode: {"api_max_concurrency": 3, "spec_batch_size": 3, "max_candidates_per_scope": 24},
    )

    started = time.perf_counter()
    items = await collector.collect_scope_candidates("business-growth-ops", max_candidates=6)
    elapsed = time.perf_counter() - started

    assert len(items) == 3
    assert elapsed < 0.12


@pytest.mark.asyncio
async def test_collect_scope_candidates_passes_comment_timeout_from_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    spec = _spec(
        scope_id="ai-automation",
        topic_pack_id="tools-efficiency",
        subreddit="ChatGPT",
        query="which ai tool did you keep",
        primary_reason="tools-efficiency:change_keyword",
    )
    seen: dict[str, float] = {}

    async def _fake_collect(reddit, scope_id, spec, *, comment_timeout, **kwargs):
        seen["comment_timeout"] = comment_timeout
        return [_candidate(spec, candidate_id="cand-chatgpt-1", post_id="chatgpt-1", title="Which AI tool did you keep?")]

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: [spec])
    monkeypatch.setattr(collector, "build_topic_pack_candidate_quotas", lambda scope_id, max_candidates: {"tools-efficiency": 1})
    monkeypatch.setattr(collector, "collect_candidates_for_spec", _fake_collect)
    monkeypatch.setattr(
        collector,
        "build_collect_reddit_client",
        lambda **kwargs: _FakeReddit(**kwargs),
    )
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)
    monkeypatch.setattr(
        collector,
        "get_supply_collect_profile",
        lambda mode: {"api_max_concurrency": 2, "spec_batch_size": 2, "comment_request_timeout": 8, "max_candidates_per_scope": 24},
    )

    items = await collector.collect_scope_candidates("ai-automation", max_candidates=4)
    assert len(items) == 1
    assert seen["comment_timeout"] == 8


@pytest.mark.asyncio
async def test_collect_scope_candidates_skips_empty_spec_results_and_keeps_other_results(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    specs = [
        _spec(
            scope_id="business-growth-ops",
            topic_pack_id="organic-discovery",
            subreddit="SEO",
            query="seo vs geo",
            primary_reason="organic-discovery:problem_keyword",
        ),
        _spec(
            scope_id="business-growth-ops",
            topic_pack_id="organic-discovery",
            subreddit="DigitalMarketing",
            query="geo replacing seo",
            primary_reason="organic-discovery:problem_keyword",
        ),
    ]

    async def _fake_collect(reddit, scope_id, spec, **kwargs):
        if spec.subreddit == "SEO":
            return []
        return [_candidate(spec, candidate_id="cand-geo-1", post_id="geo-1", title="SEO is over and now we have GEO")]

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: specs)
    monkeypatch.setattr(collector, "build_topic_pack_candidate_quotas", lambda scope_id, max_candidates: {"organic-discovery": 2})
    monkeypatch.setattr(collector, "collect_candidates_for_spec", _fake_collect)
    monkeypatch.setattr(
        collector,
        "build_collect_reddit_client",
        lambda **kwargs: _FakeReddit(**kwargs),
    )
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)
    monkeypatch.setattr(
        collector,
        "get_supply_collect_profile",
        lambda mode: {"api_max_concurrency": 2, "spec_batch_size": 2, "comment_request_timeout": 4, "max_candidates_per_scope": 24},
    )

    items = await collector.collect_scope_candidates("business-growth-ops", max_candidates=4)
    assert len(items) == 1
    assert items[0].matched_subreddit == "DigitalMarketing"


@pytest.mark.asyncio
async def test_collect_scope_candidates_keeps_duplicate_post_candidates_from_distinct_specs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    specs = [
        _spec(
            scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            subreddit="OpenAI",
            query="openai revenue comparison",
            primary_reason="upstream-winds:problem_keyword",
        ),
        _spec(
            scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            subreddit="artificial",
            query="openai revenue comparison",
            primary_reason="upstream-winds:problem_keyword",
        ),
    ]

    async def _fake_collect(reddit, scope_id, spec, **kwargs):
        return [
            _candidate(
                spec,
                candidate_id=f"cand-{spec.subreddit}-shared-post",
                post_id="shared-post",
                title="OpenAI revenue comparisons are getting messy",
            )
        ]

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: specs)
    monkeypatch.setattr(collector, "build_topic_pack_candidate_quotas", lambda scope_id, max_candidates: {"upstream-winds": 4})
    monkeypatch.setattr(collector, "collect_candidates_for_spec", _fake_collect)
    monkeypatch.setattr(
        collector,
        "build_collect_reddit_client",
        lambda **kwargs: _FakeReddit(**kwargs),
    )
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)
    monkeypatch.setattr(
        collector,
        "get_supply_collect_profile",
        lambda mode: {"api_max_concurrency": 2, "spec_batch_size": 2, "comment_request_timeout": 4, "max_candidates_per_scope": 24},
    )

    items = await collector.collect_scope_candidates("ai-automation", max_candidates=4)
    assert len(items) == 2
    assert {item.post_id for item in items} == {"shared-post"}
    assert {item.matched_subreddit for item in items} == {"OpenAI", "artificial"}


@pytest.mark.asyncio
async def test_collect_scope_candidates_merges_topic_clusters_for_duplicate_candidate_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    specs = [
        _spec(
            scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            topic_cluster_id="key-people-and-route",
            subreddit="OpenAI",
            mode="listing",
        ),
        _spec(
            scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            topic_cluster_id="platform-policy-shifts",
            subreddit="OpenAI",
            mode="listing",
        ),
    ]

    async def _fake_collect(reddit, scope_id, spec, **kwargs):
        quote_count = 1 if spec.topic_cluster_id == "key-people-and-route" else 2
        return [
            _candidate(
                spec,
                candidate_id="cand-shared-post",
                post_id="shared-post",
                title="OpenAI pricing thread collided across clusters",
                subreddit="OpenAI",
                quote_count=quote_count,
            )
        ]

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: specs)
    monkeypatch.setattr(collector, "build_topic_pack_candidate_quotas", lambda scope_id, max_candidates: {"upstream-winds": 4})
    monkeypatch.setattr(collector, "collect_candidates_for_spec", _fake_collect)
    monkeypatch.setattr(
        collector,
        "build_collect_reddit_client",
        lambda **kwargs: _FakeReddit(**kwargs),
    )
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)
    monkeypatch.setattr(
        collector,
        "get_supply_collect_profile",
        lambda mode: {"api_max_concurrency": 2, "spec_batch_size": 2, "comment_request_timeout": 4, "max_candidates_per_scope": 24},
    )

    items = await collector.collect_scope_candidates("ai-automation", max_candidates=4)

    assert len(items) == 1
    assert items[0].candidate_id == "cand-shared-post"
    assert set(items[0].topic_cluster_ids) == {"key-people-and-route", "platform-policy-shifts"}


@pytest.mark.asyncio
async def test_collect_scope_candidates_promotes_grouped_candidate_for_multi_thread_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    specs = [
        _spec(
            scope_id="ai-automation",
            topic_pack_id="tools-efficiency",
            topic_cluster_id="ai-product-and-adoption",
            subreddit="ProductManagement",
            mode="listing",
        ),
        _spec(
            scope_id="ai-automation",
            topic_pack_id="tools-efficiency",
            topic_cluster_id="ai-product-and-adoption",
            subreddit="SaaS",
            mode="listing",
        ),
    ]

    async def _fake_collect(reddit, scope_id, spec, **kwargs):
        return [
            _candidate(
                spec,
                candidate_id=f"cand-{spec.subreddit}",
                post_id=f"post-{spec.subreddit}",
                title=f"title-{spec.subreddit}",
                subreddit=spec.subreddit,
            )
        ]

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: specs)
    monkeypatch.setattr(collector, "build_topic_pack_candidate_quotas", lambda scope_id, max_candidates: {"tools-efficiency": 4})
    monkeypatch.setattr(collector, "collect_candidates_for_spec", _fake_collect)
    monkeypatch.setattr(
        collector,
        "build_collect_reddit_client",
        lambda **kwargs: _FakeReddit(**kwargs),
    )
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)
    monkeypatch.setattr(
        collector,
        "get_supply_collect_profile",
        lambda mode: {"api_max_concurrency": 2, "spec_batch_size": 2, "comment_request_timeout": 4, "max_candidates_per_scope": 24},
    )

    items = await collector.collect_scope_candidates("ai-automation", max_candidates=4)

    grouped = next(item for item in items if item.candidate_id.startswith("group-ai-automation-"))
    assert grouped.thread_count == 2
    assert grouped.community_count == 2
    assert grouped.quote_count == 2
    assert grouped.topic_cluster_ids == ["ai-product-and-adoption"]


@pytest.mark.asyncio
async def test_collect_scope_candidates_accepts_candidates_without_quotes(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    class _NoCommentReddit(_FakeReddit):
        async def fetch_post_comments(self, post_id: str, **kwargs):
            self.comment_calls.append(post_id)
            self._stats["primary_comment_requests"] += 1
            return []

    spec = _spec(
        scope_id="business-growth-ops",
        topic_pack_id="organic-discovery",
        subreddit="SEO",
        query="seo vs geo",
        primary_reason="organic-discovery:problem_keyword",
    )

    async def _fake_collect(reddit, scope_id, spec, **kwargs):
        return [_candidate(spec, candidate_id="cand-seo-1", post_id="seo-1", title="SEO vs GEO is getting messy", quote_count=0)]

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: [spec])
    monkeypatch.setattr(collector, "build_topic_pack_candidate_quotas", lambda scope_id, max_candidates: {"organic-discovery": 1})
    monkeypatch.setattr(collector, "collect_candidates_for_spec", _fake_collect)
    monkeypatch.setattr(
        collector,
        "build_collect_reddit_client",
        lambda **kwargs: _NoCommentReddit(**kwargs),
    )
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)
    monkeypatch.setattr(
        collector,
        "get_supply_collect_profile",
        lambda mode: {"api_max_concurrency": 2, "spec_batch_size": 2, "comment_request_timeout": 4, "max_candidates_per_scope": 24},
    )

    items = await collector.collect_scope_candidates("business-growth-ops", max_candidates=2)
    assert len(items) == 1
    assert items[0].quote_count == 0


@pytest.mark.asyncio
async def test_collect_scope_candidates_prioritizes_recall_clusters_within_same_pack_quota(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    specs = [
        _spec(
            scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            topic_cluster_id="flagship-project-tracks",
            subreddit="OpenAI",
            query="mythos preview",
            primary_reason="upstream-winds:template_query",
        ),
        _spec(
            scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            topic_cluster_id="platform-policy-shifts",
            subreddit="ClaudeAI",
            query="api pricing update",
            primary_reason="upstream-winds:template_query",
        ),
    ]

    async def _fake_collect(reddit, scope_id, spec, **kwargs):
        return [
            _candidate(
                spec,
                candidate_id=f"cand-{spec.topic_cluster_id}",
                post_id=f"post-{spec.topic_cluster_id}",
                title=f"title-{spec.topic_cluster_id}",
                subreddit=spec.subreddit,
            )
        ]

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: specs)
    monkeypatch.setattr(collector, "build_topic_pack_candidate_quotas", lambda scope_id, max_candidates: {"upstream-winds": 1})
    monkeypatch.setattr(collector, "collect_candidates_for_spec", _fake_collect)
    monkeypatch.setattr(
        collector,
        "build_collect_reddit_client",
        lambda **kwargs: _FakeReddit(**kwargs),
    )
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)
    monkeypatch.setattr(
        collector,
        "get_supply_collect_profile",
        lambda mode: {"api_max_concurrency": 2, "spec_batch_size": 2, "comment_request_timeout": 4, "max_candidates_per_scope": 24},
    )

    items = await collector.collect_scope_candidates("ai-automation", max_candidates=1)

    assert len(items) == 1
    assert items[0].topic_cluster_id == "platform-policy-shifts"


@pytest.mark.asyncio
async def test_collect_scope_candidates_interleaves_priority_clusters_within_same_pack_quota(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    specs = [
        _spec(
            scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            topic_cluster_id="key-people-and-route",
            subreddit="OpenAI",
            mode="listing",
        ),
        _spec(
            scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            topic_cluster_id="key-people-and-route",
            subreddit="singularity",
            mode="listing",
        ),
        _spec(
            scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            topic_cluster_id="platform-policy-shifts",
            subreddit="ClaudeAI",
            mode="listing",
        ),
    ]

    async def _fake_collect(reddit, scope_id, spec, **kwargs):
        return [
            _candidate(
                spec,
                candidate_id=f"cand-{spec.subreddit}",
                post_id=f"post-{spec.subreddit}",
                title=f"title-{spec.subreddit}",
                subreddit=spec.subreddit,
            )
        ]

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: specs)
    monkeypatch.setattr(collector, "build_topic_pack_candidate_quotas", lambda scope_id, max_candidates: {"upstream-winds": 2})
    monkeypatch.setattr(collector, "collect_candidates_for_spec", _fake_collect)
    monkeypatch.setattr(
        collector,
        "build_collect_reddit_client",
        lambda **kwargs: _FakeReddit(**kwargs),
    )
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)
    monkeypatch.setattr(
        collector,
        "get_supply_collect_profile",
        lambda mode: {"api_max_concurrency": 3, "spec_batch_size": 3, "comment_request_timeout": 4, "max_candidates_per_scope": 24},
    )

    items = await collector.collect_scope_candidates("ai-automation", max_candidates=2)

    assert len(items) == 2
    assert {item.topic_cluster_id for item in items} == {"key-people-and-route", "platform-policy-shifts"}


def test_is_noise_post_detects_business_and_seller_noise() -> None:
    from app.services.hotpost.candidate_spec_collector import _is_noise_post

    assert _is_noise_post("business-growth-ops", _post("newsletter-1", "Weekly newsletter swap thread", "SEO"), "organic-discovery") is False
    assert _is_noise_post("business-growth-ops", _post("newsletter-2", "Weekly newsletter swap thread", "SEO"), "paid-economics") is True
    assert _is_noise_post("ecommerce-sellers", _post("promo-1", "Best dropshipping course right now", "AmazonSeller"), "selection-signals") is True
    assert _is_noise_post("ecommerce-sellers", _post("real-1", "Best coffee grinder for small kitchens?", "Coffee"), "selection-signals") is False


@pytest.mark.asyncio
async def test_fetch_posts_for_spec_restricts_search_to_target_subreddit() -> None:
    from app.services.hotpost.candidate_spec_collector import fetch_posts_for_spec

    spec = _spec(
        scope_id="ecommerce-sellers",
        topic_pack_id="selection-signals",
        topic_cluster_id="small-goods",
        subreddit="Frugal",
        query="cheap useful accessory",
    )
    seen: dict[str, object] = {}

    class _SearchProbe:
        async def search_subreddit_page(self, subreddit: str, query: str, **kwargs):
            seen["subreddit"] = subreddit
            seen["query"] = query
            seen["restrict_sr"] = kwargs.get("restrict_sr")
            return ([], None)

    posts = await fetch_posts_for_spec(_SearchProbe(), spec)

    assert posts == []
    assert seen == {
        "subreddit": "Frugal",
        "query": "cheap useful accessory",
        "restrict_sr": 1,
    }


def test_pack_candidate_cap_and_fetch_limits_expand_collection_surface() -> None:
    from app.services.hotpost.candidate_spec_collector import (
        pack_candidate_cap,
        pack_comments_fetch_limit,
        pack_fetch_limit,
    )
    from app.services.hotpost.source_scope_candidate_collector import _limit_specs_by_budget

    assert pack_candidate_cap("paid-economics") == 3
    assert pack_candidate_cap("selection-signals") == 3
    assert pack_candidate_cap("organic-discovery") == 8
    assert pack_candidate_cap("funnel-conversion") == 8
    assert pack_candidate_cap("category-winds") == 6
    assert pack_candidate_cap("agent-builder") == 4
    assert pack_candidate_cap("tools-efficiency") == 4
    assert pack_candidate_cap("upstream-winds") == 6
    assert pack_fetch_limit("business-growth-ops", "paid-economics", "search") == 12
    assert pack_fetch_limit("ecommerce-sellers", "selection-signals", "listing") == 12
    assert pack_comments_fetch_limit("ai-automation", "agent-builder") == 5

    specs = [
        _spec(
            scope_id="business-growth-ops",
            topic_pack_id="organic-discovery",
            subreddit=f"sub-{index}",
            query=f"query-{index}" if index < 5 else None,
            mode="search" if index < 5 else "listing",
        )
        for index in range(8)
    ]
    limited = _limit_specs_by_budget(
        specs,
        collect_defaults={"max_search_specs_per_scope": 3, "max_listing_specs_per_scope": 2},
    )
    assert len(limited) == 6
    assert [spec.mode for spec in limited] == ["listing", "listing", "listing", "search", "search", "search"]


def test_limit_specs_by_budget_prioritizes_growth_bridge_listing_specs() -> None:
    from app.services.hotpost.source_scope_candidate_collector import _limit_specs_by_budget

    specs = [
        RedditSearchSpec(
            source_scope_id="business-growth-ops",
            topic_pack_id="paid-economics",
            subreddit="PPC",
            mode="listing",
            sort="top",
            time_filter="week",
            listing_source="listing:top:week",
            primary_reason="paid-economics:listing_hot",
        ),
        RedditSearchSpec(
            source_scope_id="business-growth-ops",
            topic_pack_id="organic-discovery",
            subreddit="Emailmarketing",
            mode="listing",
            sort="top",
            time_filter="week",
            listing_source="listing:top:week",
            primary_reason="organic-discovery:listing_keyword_bridge",
        ),
        RedditSearchSpec(
            source_scope_id="business-growth-ops",
            topic_pack_id="funnel-conversion",
            subreddit="shopify",
            mode="listing",
            sort="top",
            time_filter="week",
            listing_source="listing:top:week",
            primary_reason="funnel-conversion:listing_keyword_bridge",
        ),
    ]

    limited = _limit_specs_by_budget(
        specs,
        collect_defaults={"max_search_specs_per_scope": 0, "max_listing_specs_per_scope": 2},
    )

    assert [spec.topic_pack_id for spec in limited] == ["organic-discovery", "funnel-conversion"]


def test_limit_specs_by_budget_prioritizes_recall_clusters_inside_backfill_budget() -> None:
    from app.services.hotpost.source_scope_candidate_collector import _limit_specs_by_budget

    specs = [
        RedditSearchSpec(
            source_scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            topic_cluster_id="flagship-project-tracks",
            topic_cluster_ids=["flagship-project-tracks"],
            subreddit="OpenAI",
            mode="listing",
            sort="top",
            time_filter="week",
            listing_source="listing:top:week",
            primary_reason="upstream-winds:listing_top",
        ),
        RedditSearchSpec(
            source_scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            topic_cluster_id="platform-policy-shifts",
            topic_cluster_ids=["platform-policy-shifts"],
            subreddit="ClaudeAI",
            mode="listing",
            sort="top",
            time_filter="week",
            listing_source="listing:top:week",
            primary_reason="upstream-winds:listing_top",
        ),
    ]

    limited = _limit_specs_by_budget(
        specs,
        collect_defaults={"max_search_specs_per_scope": 0, "max_listing_specs_per_scope": 1},
    )

    assert len(limited) == 1
    assert limited[0].topic_cluster_id == "platform-policy-shifts"


def test_prioritize_specs_for_recall_interleaves_priority_clusters_within_pack() -> None:
    from app.services.hotpost.source_scope_candidate_collector import _prioritize_specs_for_recall

    specs = [
        _spec(
            scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            topic_cluster_id="key-people-and-route",
            subreddit="OpenAI",
            mode="listing",
        ),
        _spec(
            scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            topic_cluster_id="key-people-and-route",
            subreddit="singularity",
            mode="listing",
        ),
        _spec(
            scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            topic_cluster_id="platform-policy-shifts",
            subreddit="ClaudeAI",
            mode="listing",
        ),
        _spec(
            scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            topic_cluster_id="flagship-project-tracks",
            subreddit="MachineLearning",
            mode="listing",
        ),
    ]

    prioritized = _prioritize_specs_for_recall(specs)

    assert [spec.topic_cluster_id for spec in prioritized[:4]] == [
        "key-people-and-route",
        "platform-policy-shifts",
        "key-people-and-route",
        "flagship-project-tracks",
    ]


def test_prioritize_specs_for_recall_interleaves_non_priority_clusters_within_pack() -> None:
    from app.services.hotpost.source_scope_candidate_collector import _prioritize_specs_for_recall

    specs = [
        _spec(
            scope_id="ecommerce-sellers",
            topic_pack_id="selection-signals",
            topic_cluster_id="pet",
            subreddit="petproducts",
        ),
        _spec(
            scope_id="ecommerce-sellers",
            topic_pack_id="selection-signals",
            topic_cluster_id="pet",
            subreddit="BuyItForLife",
        ),
        _spec(
            scope_id="ecommerce-sellers",
            topic_pack_id="selection-signals",
            topic_cluster_id="small-goods",
            subreddit="EtsySellers",
        ),
        _spec(
            scope_id="ecommerce-sellers",
            topic_pack_id="selection-signals",
            topic_cluster_id="home",
            subreddit="homeowners",
        ),
        _spec(
            scope_id="ecommerce-sellers",
            topic_pack_id="selection-signals",
            topic_cluster_id="small-goods",
            subreddit="AmazonSeller",
        ),
    ]

    prioritized = _prioritize_specs_for_recall(specs)

    assert [spec.topic_cluster_id for spec in prioritized[:5]] == [
        "pet",
        "small-goods",
        "home",
        "pet",
        "small-goods",
    ]


@pytest.mark.asyncio
async def test_collect_scope_candidates_interleaves_non_priority_clusters_when_pack_quota_is_small(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    specs = [
        _spec(
            scope_id="ecommerce-sellers",
            topic_pack_id="selection-signals",
            topic_cluster_id="pet",
            subreddit="petproducts",
            query="pet hair remover",
        ),
        _spec(
            scope_id="ecommerce-sellers",
            topic_pack_id="selection-signals",
            topic_cluster_id="pet",
            subreddit="BuyItForLife",
            query="dog travel accessory",
        ),
        _spec(
            scope_id="ecommerce-sellers",
            topic_pack_id="selection-signals",
            topic_cluster_id="small-goods",
            subreddit="EtsySellers",
            query="small product niche",
        ),
    ]

    async def _fake_collect(reddit, scope_id, spec, **kwargs):
        return [
            _candidate(
                spec,
                candidate_id=f"cand-{spec.subreddit}",
                post_id=f"post-{spec.subreddit}",
                title=f"title-{spec.subreddit}",
                subreddit=spec.subreddit,
            )
        ]

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: specs)
    monkeypatch.setattr(collector, "build_topic_pack_candidate_quotas", lambda scope_id, max_candidates: {"selection-signals": 2})
    monkeypatch.setattr(collector, "collect_candidates_for_spec", _fake_collect)
    monkeypatch.setattr(
        collector,
        "build_collect_reddit_client",
        lambda **kwargs: _FakeReddit(**kwargs),
    )
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)
    monkeypatch.setattr(
        collector,
        "get_supply_collect_profile",
        lambda mode: {"api_max_concurrency": 3, "spec_batch_size": 3, "comment_request_timeout": 4, "max_candidates_per_scope": 24},
    )

    items = await collector.collect_scope_candidates("ecommerce-sellers", max_candidates=2)

    assert len(items) == 2
    assert {item.topic_cluster_id for item in items} == {"pet", "small-goods"}


def test_limit_specs_by_budget_preserves_discover_before_backfill() -> None:
    from app.services.hotpost.source_scope_candidate_collector import _limit_specs_by_budget

    specs = [
        RedditSearchSpec(
            source_scope_id="business-growth-ops",
            topic_pack_id="organic-discovery",
            subreddit="Emailmarketing",
            mode="listing",
            sort="hot",
            time_filter="day",
            listing_source="listing:hot:day",
            primary_reason="organic-discovery:listing_keyword_bridge",
        ),
        RedditSearchSpec(
            source_scope_id="business-growth-ops",
            topic_pack_id="funnel-conversion",
            subreddit="shopify",
            mode="listing",
            sort="hot",
            time_filter="day",
            listing_source="listing:hot:day",
            primary_reason="funnel-conversion:listing_keyword_bridge",
        ),
        RedditSearchSpec(
            source_scope_id="business-growth-ops",
            topic_pack_id="paid-economics",
            subreddit="PPC",
            mode="listing",
            sort="top",
            time_filter="week",
            listing_source="listing:top:week",
            primary_reason="paid-economics:listing_top",
        ),
    ]

    limited = _limit_specs_by_budget(
        specs,
        collect_defaults={"max_search_specs_per_scope": 0, "max_listing_specs_per_scope": 0},
    )

    assert [spec.topic_pack_id for spec in limited] == ["organic-discovery", "funnel-conversion"]


def test_limit_specs_by_budget_ratchets_down_backfill_after_dry_cycles() -> None:
    from app.services.hotpost.source_scope_candidate_collector import _limit_specs_by_budget

    specs = [
        RedditSearchSpec(
            source_scope_id="business-growth-ops",
            topic_pack_id="organic-discovery",
            subreddit="Emailmarketing",
            mode="listing",
            sort="hot",
            time_filter="day",
            listing_source="listing:hot:day",
            primary_reason="organic-discovery:listing_keyword_bridge",
        ),
        RedditSearchSpec(
            source_scope_id="business-growth-ops",
            topic_pack_id="funnel-conversion",
            subreddit="shopify",
            mode="listing",
            sort="new",
            time_filter="day",
            listing_source="listing:new:day",
            primary_reason="funnel-conversion:listing_keyword_bridge",
        ),
        RedditSearchSpec(
            source_scope_id="business-growth-ops",
            topic_pack_id="paid-economics",
            subreddit="PPC",
            mode="listing",
            sort="top",
            time_filter="week",
            listing_source="listing:top:week",
            primary_reason="paid-economics:listing_top",
        ),
        RedditSearchSpec(
            source_scope_id="business-growth-ops",
            topic_pack_id="paid-economics",
            subreddit="FacebookAds",
            mode="listing",
            sort="top",
            time_filter="week",
            listing_source="listing:top:week",
            primary_reason="paid-economics:listing_top",
        ),
        RedditSearchSpec(
            source_scope_id="business-growth-ops",
            topic_pack_id="paid-economics",
            subreddit="PPC",
            mode="search",
            sort="relevance",
            time_filter="week",
            query="rising cpc",
            listing_source="search:relevance:week",
            primary_reason="paid-economics:problem_keyword",
        ),
        RedditSearchSpec(
            source_scope_id="business-growth-ops",
            topic_pack_id="paid-economics",
            subreddit="FacebookAds",
            mode="search",
            sort="relevance",
            time_filter="week",
            query="junk clicks",
            listing_source="search:relevance:week",
            primary_reason="paid-economics:problem_keyword",
        ),
    ]

    collect_defaults = {"max_search_specs_per_scope": 2, "max_listing_specs_per_scope": 2}

    first_dry = _limit_specs_by_budget(specs, collect_defaults=collect_defaults, dry_cycles=1)
    second_dry = _limit_specs_by_budget(specs, collect_defaults=collect_defaults, dry_cycles=2)

    assert [spec.topic_pack_id for spec in first_dry] == [
        "organic-discovery",
        "funnel-conversion",
        "paid-economics",
        "paid-economics",
    ]
    assert [spec.mode for spec in first_dry] == ["listing", "listing", "listing", "search"]
    assert [spec.topic_pack_id for spec in second_dry] == ["organic-discovery", "funnel-conversion"]


@pytest.mark.asyncio
async def test_comment_enrichment_batch_timeout_cancels_stuck_tasks() -> None:
    from app.services.hotpost.candidate_spec_collector import _await_comment_tasks, _task_comments_or_empty

    gate = asyncio.Event()

    async def _never_finishes() -> list[dict]:
        await gate.wait()
        return [{"body": "late"}]

    task = asyncio.create_task(_never_finishes())

    await _await_comment_tasks([task], timeout_seconds=0.01, log_context={"phase": "test"})

    assert task.cancelled()
    assert _task_comments_or_empty(task, log_context={"phase": "test"}) == []


@pytest.mark.asyncio
async def test_comment_enrichment_batch_timeout_keeps_completed_results() -> None:
    from app.services.hotpost.candidate_spec_collector import _await_comment_tasks, _task_comments_or_empty

    async def _done() -> list[dict]:
        await asyncio.sleep(0)
        return [{"body": "useful"}]

    task = asyncio.create_task(_done())

    await _await_comment_tasks([task], timeout_seconds=0.5, log_context={"phase": "test"})

    assert _task_comments_or_empty(task, log_context={"phase": "test"}) == [{"body": "useful"}]


@pytest.mark.asyncio
async def test_collect_candidates_for_spec_extends_comment_wait_for_sociavault_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import candidate_spec_collector as collector

    spec = _spec(
        scope_id="business-growth-ops",
        topic_pack_id="funnel-conversion",
        subreddit="analytics",
        query="ga4 attribution mismatch",
        primary_reason="funnel-conversion:named_topic",
    )
    seen: dict[str, float] = {}

    class _RedditWithFallback:
        fallback = SimpleNamespace(request_timeout=20.0)

        def should_skip_comment_fetch(self) -> bool:
            return False

        async def search_subreddit_page(self, subreddit: str, query: str, **kwargs):
            return ([_post("ga4-1", "GA4 attribution mismatch", subreddit)], None)

        async def fetch_post_comments(self, post_id: str, **kwargs):
            return []

    async def _capture_comment_wait(tasks, *, timeout_seconds, log_context):
        seen["timeout_seconds"] = timeout_seconds
        await asyncio.gather(*tasks)

    monkeypatch.setattr(collector, "_await_comment_tasks", _capture_comment_wait)

    await collector.collect_candidates_for_spec(
        _RedditWithFallback(),
        "business-growth-ops",
        spec,
        collect_batch_id="batch-1",
        collected_at=datetime.fromtimestamp(1_775_200_000, timezone.utc),
        comment_timeout=8,
        comment_cache={},
        comment_tasks={},
    )

    assert seen["timeout_seconds"] == 32.0


def test_prioritize_discover_specs_for_assist_brings_secondary_specs_forward() -> None:
    from app.services.hotpost.source_scope_candidate_collector import _prioritize_discover_specs_for_assist

    specs = [
        _spec(
            scope_id="business-growth-ops",
            topic_pack_id="organic-discovery",
            subreddit=f"primary-{index}",
            mode="listing",
            primary_reason="organic-discovery:listing_keyword_bridge",
        )
        for index in range(6)
    ]
    secondary = [
        _spec(
            scope_id="business-growth-ops",
            topic_pack_id="paid-economics",
            subreddit=f"secondary-{index}",
            mode="listing",
            primary_reason="paid-economics:listing_keyword_bridge",
        ).model_copy(update={"sort": "new", "listing_source": "listing:new:day"})
        for index in range(2)
    ]

    prioritized = _prioritize_discover_specs_for_assist(
        [*specs, *secondary],
        phase="discover",
        assist_secondary_discover=True,
        spec_batch_size=2,
    )

    assert [spec.subreddit for spec in prioritized[:6]] == [
        "primary-0",
        "primary-1",
        "primary-2",
        "primary-3",
        "secondary-0",
        "secondary-1",
    ]


@pytest.mark.asyncio
async def test_collect_scope_candidates_uses_safe_profile_defaults_when_mode_is_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    spec = _spec(
        scope_id="business-growth-ops",
        topic_pack_id="organic-discovery",
        subreddit="SEO",
        query="seo vs geo",
        primary_reason="organic-discovery:problem_keyword",
    )
    seen: dict[str, object] = {}

    class _SeenReddit(_FakeReddit):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            seen["reddit_kwargs"] = kwargs

    async def _fake_collect(*args, **kwargs):
        return []

    def _fake_quotas(scope_id, max_candidates):
        seen["quota"] = max_candidates
        return {"organic-discovery": max_candidates}

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: [spec] * 10)
    monkeypatch.setattr(collector, "build_topic_pack_candidate_quotas", _fake_quotas)
    monkeypatch.setattr(collector, "collect_candidates_for_spec", _fake_collect)
    monkeypatch.setattr(
        collector,
        "build_collect_reddit_client",
        lambda **kwargs: _SeenReddit(**kwargs),
    )
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)
    monkeypatch.setattr(
        collector,
        "get_supply_collect_profile",
        lambda mode: {
            "max_candidates_per_scope": 12,
            "comment_request_timeout": 4,
            "api_max_concurrency": 3,
            "low_quota_remaining_threshold": 12,
            "low_quota_cooldown_seconds": 20,
            "stop_comment_fetch_below_remaining": 24,
            "max_consecutive_rate_limit_errors": 3,
            "spec_batch_size": 4,
            "max_search_specs_per_scope": 2,
            "max_listing_specs_per_scope": 1,
        },
    )

    await collector.collect_scope_candidates("business-growth-ops", mode="safe")

    assert seen["quota"] == 12
    assert seen["reddit_kwargs"]["max_concurrency"] == 3


@pytest.mark.asyncio
async def test_collect_scope_candidates_runs_discover_enrich_backfill_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    discover_spec = _spec(
        scope_id="business-growth-ops",
        topic_pack_id="organic-discovery",
        subreddit="content_marketing",
        mode="listing",
        primary_reason="organic-discovery:listing_keyword_bridge",
    )
    backfill_spec = _spec(
        scope_id="business-growth-ops",
        topic_pack_id="paid-economics",
        subreddit="PPC",
        query="meta roas",
        mode="search",
        primary_reason="paid-economics:problem_keyword",
    )
    calls: list[tuple[str, bool, tuple[str, ...] | None]] = []
    seen_reddit: _FakeReddit | None = None

    async def _fake_collect(reddit, scope_id, spec, *, enrich_comments, selected_post_ids=None, **kwargs):
        calls.append(
            (
                spec.topic_pack_id,
                enrich_comments,
                tuple(sorted(selected_post_ids)) if selected_post_ids is not None else None,
            )
        )
        candidate_id = f"cand-{spec.topic_pack_id}"
        post_id = "post-organic" if spec.topic_pack_id == "organic-discovery" else "post-paid"
        title = "Need a New Payment Processor" if spec.topic_pack_id == "paid-economics" else "Content marketing feels broken"
        return [_candidate(spec, candidate_id=candidate_id, post_id=post_id, title=title, quote_count=0)]

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: [discover_spec, backfill_spec])
    monkeypatch.setattr(
        collector,
        "build_topic_pack_candidate_quotas",
        lambda scope_id, max_candidates: {"organic-discovery": 2, "paid-economics": 2},
    )
    monkeypatch.setattr(collector, "collect_candidates_for_spec", _fake_collect)

    def _build_reddit(**kwargs):
        nonlocal seen_reddit
        seen_reddit = _FakeReddit(**kwargs)
        return seen_reddit

    monkeypatch.setattr(collector, "build_collect_reddit_client", _build_reddit)
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)
    monkeypatch.setattr(
        collector,
        "get_supply_collect_profile",
        lambda mode: {
            "max_candidates_per_scope": 8,
            "comment_request_timeout": 8,
            "api_max_concurrency": 2,
            "low_quota_remaining_threshold": 25,
            "low_quota_cooldown_seconds": 20,
            "stop_comment_fetch_below_remaining": 30,
            "max_consecutive_rate_limit_errors": 3,
            "spec_batch_size": 2,
            "max_search_specs_per_scope": 2,
            "max_listing_specs_per_scope": 2,
        },
    )

    items = await collector.collect_scope_candidates("business-growth-ops", max_candidates=4)

    assert [item.topic_pack_id for item in items] == ["organic-discovery", "paid-economics"]
    assert calls[0] == ("organic-discovery", False, None)
    assert calls[1] == ("paid-economics", False, None)
    assert seen_reddit is not None
    assert seen_reddit.comment_calls == ["post-organic", "post-paid"]
    organic = next(item for item in items if item.topic_pack_id == "organic-discovery")
    paid = next(item for item in items if item.topic_pack_id == "paid-economics")
    assert organic.quote_count == 1
    assert organic.evidence_quotes[0].text == "This is a useful quote with enough detail."
    assert paid.quote_count == 1
    assert paid.evidence_quotes[0].text == "This is a useful quote with enough detail."


@pytest.mark.asyncio
async def test_collect_scope_candidates_keeps_reddit_api_primary_for_discover_even_after_two_dry_cycles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    spec = _spec(
        scope_id="business-growth-ops",
        topic_pack_id="organic-discovery",
        subreddit="content_marketing",
        mode="listing",
        primary_reason="organic-discovery:listing_keyword_bridge",
    )
    seen: dict[str, object] = {}

    async def _fake_collect(*args, **kwargs):
        return []

    class _SeenReddit(_FakeReddit):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            seen.update(kwargs)

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: [spec])
    monkeypatch.setattr(collector, "build_topic_pack_candidate_quotas", lambda scope_id, max_candidates: {"organic-discovery": 1})
    monkeypatch.setattr(collector, "collect_candidates_for_spec", _fake_collect)
    monkeypatch.setattr(collector, "build_collect_reddit_client", lambda **kwargs: _SeenReddit(**kwargs))
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)
    monkeypatch.setattr(
        collector,
        "get_supply_collect_profile",
        lambda mode: {
            "max_candidates_per_scope": 8,
            "comment_request_timeout": 8,
            "api_max_concurrency": 2,
            "low_quota_remaining_threshold": 25,
            "low_quota_cooldown_seconds": 20,
            "stop_comment_fetch_below_remaining": 30,
            "max_consecutive_rate_limit_errors": 3,
            "spec_batch_size": 2,
            "max_search_specs_per_scope": 2,
            "max_listing_specs_per_scope": 2,
        },
    )

    await collector.collect_scope_candidates("business-growth-ops", mode="safe", dry_cycles=2)

    assert "prefer_fallback_for_posts" not in seen


@pytest.mark.asyncio
async def test_collect_scope_candidates_only_offloads_secondary_discover_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    primary_discover = _spec(
        scope_id="business-growth-ops",
        topic_pack_id="organic-discovery",
        subreddit="content_marketing",
        mode="listing",
        primary_reason="organic-discovery:listing_keyword_bridge",
    )
    secondary_discover = _spec(
        scope_id="business-growth-ops",
        topic_pack_id="organic-discovery",
        subreddit="TechSEO",
        mode="listing",
        primary_reason="organic-discovery:listing_keyword_bridge",
    )
    secondary_discover = secondary_discover.model_copy(
        update={
            "sort": "new",
            "listing_source": "listing:new:day",
        }
    )
    seen: list[tuple[str, str, bool]] = []

    async def _fake_collect(reddit, scope_id, spec, *, prefer_fallback_for_posts=False, **kwargs):
        seen.append((spec.subreddit, spec.sort, prefer_fallback_for_posts))
        return []

    monkeypatch.setattr(collector, "build_reddit_search_specs", lambda scope_id: [primary_discover, secondary_discover])
    monkeypatch.setattr(
        collector,
        "build_topic_pack_candidate_quotas",
        lambda scope_id, max_candidates: {"organic-discovery": 2},
    )
    monkeypatch.setattr(collector, "collect_candidates_for_spec", _fake_collect)
    monkeypatch.setattr(collector, "build_collect_reddit_client", lambda **kwargs: _FakeReddit(**kwargs))
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)
    monkeypatch.setattr(
        collector,
        "get_supply_collect_profile",
        lambda mode: {
            "max_candidates_per_scope": 8,
            "comment_request_timeout": 8,
            "api_max_concurrency": 2,
            "low_quota_remaining_threshold": 25,
            "low_quota_cooldown_seconds": 20,
            "stop_comment_fetch_below_remaining": 30,
            "max_consecutive_rate_limit_errors": 3,
            "spec_batch_size": 2,
            "max_search_specs_per_scope": 2,
            "max_listing_specs_per_scope": 2,
        },
    )

    await collector.collect_scope_candidates(
        "business-growth-ops",
        mode="safe",
        dry_cycles=2,
        enable_secondary_discover_assist=True,
    )

    assert seen == [
        ("content_marketing", "hot", False),
        ("TechSEO", "new", True),
    ]
