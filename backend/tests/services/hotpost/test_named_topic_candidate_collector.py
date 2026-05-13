from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.schemas.hotpost_card_candidates import CandidatePack


def _candidate(candidate_id: str, query: str) -> CandidatePack:
    return CandidatePack.model_validate(
        {
            "candidate_id": candidate_id,
            "signal_id": f"sig-{candidate_id}",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 自动化",
            "topic_pack_id": "upstream-winds",
            "query": query,
            "matched_subreddit": "LLM",
            "post_id": f"post-{candidate_id}",
            "title": f"title-{candidate_id}",
            "score": 60,
            "num_comments": 20,
            "created_at": "2026-04-11T00:00:00Z",
            "collected_at": "2026-04-11T00:00:00Z",
            "collect_batch_id": "batch-1",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "new_threads_24h",
            "listing_source": "named-topic-search:relevance:week",
            "primary_reason": "upstream-winds:named_topic",
            "matched_keywords": ["claude-mythos"],
            "top_communities": ["r/LLM"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 1,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [
                {
                    "text": "Claude Mythos is everywhere this week.",
                    "community": "r/LLM",
                    "permalink": f"https://www.reddit.com/r/LLM/comments/post-{candidate_id}/q1",
                }
            ],
        }
    )


def test_collect_named_topic_candidates_persists_unique_candidates(monkeypatch) -> None:
    from app.services.hotpost import named_topic_candidate_collector as mod

    saved: list[CandidatePack] = []

    class _FakeRedditClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def _fake_collect_candidates_for_spec(_reddit, _scope_id, spec, **kwargs):
        slug = spec.query.replace(" ", "-")
        return [_candidate(f"cand-{slug}", spec.query)]

    monkeypatch.setattr(
        mod,
        "build_collect_reddit_client",
        lambda **kwargs: _FakeRedditClient(),
    )
    monkeypatch.setattr(mod, "collect_candidates_for_spec", _fake_collect_candidates_for_spec)
    monkeypatch.setattr(mod, "upsert_candidate", lambda item: saved.append(item) or item)

    watch = mod.build_custom_named_topic_watch(
        topic_id="claude-mythos",
        scope_id="ai-automation",
        topic_pack_id="upstream-winds",
        queries=["claude mythos", "claude mythos"],
        subreddits=["LLM"],
        candidate_cap=4,
    )

    items = asyncio.run(mod.collect_named_topic_candidates([watch], persist=True))

    assert len(items) == 1
    assert len(saved) == 1
    assert items[0].candidate_id == "cand-claude-mythos"


def test_collect_named_topic_candidates_can_skip_comment_enrichment(monkeypatch) -> None:
    from app.services.hotpost import named_topic_candidate_collector as mod

    calls: list[bool] = []

    class _FakeRedditClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def _fake_collect_candidates_for_spec(_reddit, _scope_id, spec, **kwargs):
        calls.append(bool(kwargs.get("enrich_comments")))
        return [_candidate("cand-no-comments", spec.query)]

    monkeypatch.setattr(mod, "build_collect_reddit_client", lambda **kwargs: _FakeRedditClient())
    monkeypatch.setattr(mod, "collect_candidates_for_spec", _fake_collect_candidates_for_spec)
    monkeypatch.setattr(mod, "upsert_candidate", lambda item: item)

    watch = mod.build_custom_named_topic_watch(
        topic_id="ai-product-adoption",
        scope_id="ai-automation",
        topic_pack_id="tools-efficiency",
        queries=["ai product adoption"],
        subreddits=["ProductManagement"],
        candidate_cap=1,
    )

    items = asyncio.run(mod.collect_named_topic_candidates([watch], persist=True, enrich_comments=False))

    assert len(items) == 1
    assert calls == [False]


def test_named_topic_spec_carries_named_topic_and_cluster_metadata() -> None:
    from app.services.hotpost.named_topic_candidate_collector import _build_named_topic_spec, build_custom_named_topic_watch

    watch = build_custom_named_topic_watch(
        topic_id="karpathy-llm-wiki",
        scope_id="ai-automation",
        topic_pack_id="upstream-winds",
        topic_cluster_ids=["key-people-and-route"],
        queries=["karpathy llm wiki"],
        subreddits=["LLM"],
    )

    spec = _build_named_topic_spec(watch, subreddit="LLM", query="karpathy llm wiki")

    assert spec.topic_cluster_id == "key-people-and-route"
    assert spec.topic_cluster_ids == ["key-people-and-route"]
    assert spec.named_topic_ids == ["karpathy-llm-wiki"]


def test_named_topic_spec_respects_month_time_filter() -> None:
    from app.services.hotpost.named_topic_candidate_collector import _build_named_topic_spec, build_custom_named_topic_watch

    watch = build_custom_named_topic_watch(
        topic_id="small-goods-watch",
        scope_id="ecommerce-sellers",
        topic_pack_id="selection-signals",
        topic_cluster_ids=["small-goods"],
        queries=["cheap useful accessory"],
        subreddits=["BuyItForLife"],
        time_filter="month",
    )

    spec = _build_named_topic_spec(watch, subreddit="BuyItForLife", query="cheap useful accessory")

    assert spec.time_filter == "month"
    assert spec.listing_source == "named-topic-search:relevance:month"
