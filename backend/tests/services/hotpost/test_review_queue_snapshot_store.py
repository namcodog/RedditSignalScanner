from __future__ import annotations

from pathlib import Path

import pytest


def _candidate_payload(candidate_id: str = "cand-a") -> dict:
    return {
        "candidate_id": candidate_id,
        "signal_id": f"sig-{candidate_id}",
        "source_scope_id": "ai-automation",
        "source_scope_name": "AI 自动化",
        "topic_pack_id": "upstream-winds",
        "query": "karpathy llm wiki",
        "matched_subreddit": "LLM",
        "post_id": f"post-{candidate_id}",
        "title": f"title-{candidate_id}",
        "score": 42,
        "num_comments": 12,
        "created_at": "2026-04-11T00:00:00Z",
        "collected_at": "2026-04-11T00:00:00Z",
        "collect_batch_id": "batch-1",
        "time_window": "7d",
        "signal_level": "rising",
        "why_now_reason": "new_threads_24h",
        "listing_source": "named-topic-search:relevance:week",
        "primary_reason": "upstream-winds:named_topic",
        "matched_keywords": ["karpathy-llm-wiki"],
        "top_communities": ["r/LLM"],
        "thread_count": 1,
        "community_count": 1,
        "quote_count": 1,
        "intent_tags": ["趋势变化"],
        "evidence_quotes": [
            {
                "text": "Karpathy's LLM wiki pattern is everywhere this week.",
                "community": "r/LLM",
                "permalink": "https://www.reddit.com/r/LLM/comments/post-cand-a/q1",
            }
        ],
    }


def test_review_queue_snapshot_round_trip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.services.hotpost import review_queue_snapshot_store as mod

    monkeypatch.setattr(mod, "_SNAPSHOT_ROOT", tmp_path / "review_queue")
    monkeypatch.setattr(mod, "_SNAPSHOTS_DIR", mod._SNAPSHOT_ROOT / "snapshots")
    monkeypatch.setattr(mod, "_LATEST_PATH", mod._SNAPSHOT_ROOT / "latest.json")

    candidate = CandidatePack.model_validate(_candidate_payload())
    snapshot_id = mod.write_review_queue_snapshot(
        card_type="validate",
        scope="ai-automation",
        level="rising",
        limit=10,
        candidates=[candidate],
    )

    payload = mod.load_review_queue_snapshot()
    restored = mod.get_snapshot_candidate("cand-a")

    assert payload["snapshot_id"] == snapshot_id
    assert payload["candidate_count"] == 1
    assert restored.candidate_id == "cand-a"
    assert restored.topic_pack_id == "upstream-winds"


def test_review_queue_snapshot_requires_latest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services.hotpost import review_queue_snapshot_store as mod

    monkeypatch.setattr(mod, "_SNAPSHOT_ROOT", tmp_path / "review_queue")
    monkeypatch.setattr(mod, "_SNAPSHOTS_DIR", mod._SNAPSHOT_ROOT / "snapshots")
    monkeypatch.setattr(mod, "_LATEST_PATH", mod._SNAPSHOT_ROOT / "latest.json")

    with pytest.raises(LookupError, match="Run `review_cards.py queue` first"):
        mod.load_review_queue_snapshot()
