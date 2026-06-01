from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.schemas.hotpost_card_candidates import CandidatePack


def _seeded_path(tmp_path: Path) -> Path:
    path = tmp_path / "hotpost_cards.json"
    path.write_text(
        '{"categories":[],"candidates":[],"drafts":[],"published":[]}',
        encoding="utf-8",
    )
    return path


def _candidate(candidate_id: str = "cand-pipeline-001") -> CandidatePack:
    return CandidatePack.model_validate(
        {
            "candidate_id": candidate_id,
            "signal_id": f"sig-{candidate_id}",
            "source_scope_id": "business-growth-ops",
            "source_scope_name": "商业增长与运营",
            "topic_pack_id": "paid-economics",
            "query": "lead quality",
            "matched_subreddit": "PPC",
            "post_id": f"post-{candidate_id}",
            "title": "Lead quality changed",
            "score": 18,
            "num_comments": 9,
            "created_at": "2026-04-11T00:00:00Z",
            "collected_at": "2026-04-11T00:00:00Z",
            "collect_batch_id": "batch-1",
            "time_window": "7d",
            "signal_level": "rising",
            "why_now_reason": "recurring_7d",
            "listing_source": "search:relevance:week",
            "primary_reason": "paid-economics:problem_keyword",
            "matched_keywords": ["lead quality"],
            "top_communities": ["r/PPC"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 1,
            "intent_tags": ["求建议"],
            "evidence_quotes": [
                {
                    "text": "I switched goals and lead quality cratered.",
                    "community": "r/PPC",
                    "permalink": f"https://www.reddit.com/r/PPC/comments/post-{candidate_id}/q1",
                }
            ],
        }
    )


@pytest.mark.asyncio
async def test_seed_review_draft_blocks_published_duplicate_before_model_call(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services.hotpost import card_payload_store
    from app.services.hotpost import review_card_ops as mod
    from app.services.hotpost.card_draft_builder import seed_validation_draft

    candidate = _candidate()
    seeded = seed_validation_draft(candidate)
    path = _seeded_path(tmp_path)
    path.write_text(
        json.dumps(
            {
                "categories": [],
                "candidates": [],
                "drafts": [],
                "published": [{"card_id": seeded.card_id}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)
    monkeypatch.setattr(mod, "save_generation_trace", lambda *args, **kwargs: None)

    async def _unexpected_generate(*args, **kwargs):
        raise AssertionError("model generation should not run for duplicates")

    monkeypatch.setattr(mod, "generate_card_content", _unexpected_generate)

    with pytest.raises(ValueError, match="Published card already exists"):
        await mod.seed_review_draft_from_candidate(candidate, "validate")


@pytest.mark.asyncio
async def test_seed_review_validate_disables_hidden_breakdown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services.hotpost import card_payload_store
    from app.services.hotpost import review_card_ops as mod

    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", _seeded_path(tmp_path))
    monkeypatch.setattr(mod, "save_generation_trace", lambda *args, **kwargs: None)
    seen: dict[str, object] = {}

    async def _fake_generate(draft, *, allow_breakdown: bool = True):
        seen["allow_breakdown"] = allow_breakdown
        return draft

    monkeypatch.setattr(mod, "generate_card_content", _fake_generate)

    await mod.seed_review_draft_from_candidate(_candidate("cand-no-breakdown"), "validate")

    assert seen["allow_breakdown"] is False


@pytest.mark.asyncio
async def test_seed_review_trace_includes_generation_sub_stages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.services.hotpost import card_content_generator
    from app.services.hotpost import card_payload_store
    from app.services.hotpost import review_card_ops as mod

    class JsonClient:
        async def generate(self, *_args, **_kwargs) -> str:
            return '{"title":"ok"}'

    captured: dict[str, object] = {}

    def _capture_trace(trace_id: str, payload: dict) -> None:
        captured["trace_id"] = trace_id
        captured["payload"] = payload

    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", _seeded_path(tmp_path))
    monkeypatch.setattr(mod, "save_generation_trace", _capture_trace)

    async def _fake_generate(draft, *, allow_breakdown: bool = True):
        await card_content_generator._generate_json(
            model="deepseek/deepseek-v4-pro",
            timeout=30.0,
            messages=[{"role": "system", "content": "return json"}],
            client_factory=lambda _model, _timeout: JsonClient(),
            stage="writer",
            trace_id=draft.draft_id,
        )
        return draft

    monkeypatch.setattr(mod, "generate_card_content", _fake_generate)

    await mod.seed_review_draft_from_candidate(_candidate("cand-trace-substage"), "validate")

    payload = captured["payload"]
    assert payload["overall_status"] == "completed"
    assert payload["sub_stages"][0]["name"] == "writer"
    assert payload["sub_stages"][0]["status"] == "completed"
    assert payload["sub_stages"][0]["model"] == "deepseek/deepseek-v4-pro"
