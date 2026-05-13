from __future__ import annotations

import argparse
from types import SimpleNamespace

import pytest

from app.schemas.hotpost_card_candidates import CandidatePack


def _candidate() -> CandidatePack:
    return CandidatePack.model_validate(
        {
            "candidate_id": "cand-review-001",
            "signal_id": "sig-review-001",
            "source_scope_id": "business-growth-ops",
            "source_scope_name": "商业增长与运营",
            "topic_pack_id": "paid-economics",
            "query": "google ads lead quality",
            "matched_subreddit": "googleads",
            "post_id": "post-review-001",
            "title": "Google Ads 新手求助",
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
            "top_communities": ["r/googleads"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 1,
            "intent_tags": ["求建议"],
            "evidence_quotes": [
                {
                    "text": "I switched goals and lead quality cratered.",
                    "community": "r/googleads",
                    "permalink": "https://www.reddit.com/r/googleads/comments/post-review-001/q1",
                }
            ],
        }
    )


def test_queue_cmd_writes_review_snapshot(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import backend.scripts.hotpost.review_cards as mod

    candidate = _candidate()
    captured: dict[str, object] = {}
    monkeypatch.setattr(mod, "load_published_cards", lambda: [])
    monkeypatch.setattr(mod, "list_drafts", lambda *args, **kwargs: [])
    monkeypatch.setattr(mod, "list_candidates", lambda scope, level: [candidate])
    monkeypatch.setattr(mod, "filter_actionable_candidates", lambda items, **kwargs: items)
    monkeypatch.setattr(mod, "prioritize_validate_candidates", lambda items, **kwargs: items)
    monkeypatch.setattr(mod, "score_validate_candidate", lambda *args, **kwargs: (0, ["fresh"]))
    monkeypatch.setattr(mod, "seed_validation_draft", lambda item: SimpleNamespace(lane="signal"))
    monkeypatch.setattr(
        mod,
        "write_review_queue_snapshot",
        lambda **kwargs: captured.update(kwargs) or "queue-20260411-abcd1234",
    )

    mod.queue_cmd(argparse.Namespace(scope=None, level=None, type="validate", limit=10))

    output = capsys.readouterr().out
    assert "snapshot_id=queue-20260411-abcd1234" in output
    assert captured["card_type"] == "validate"
    assert [item.candidate_id for item in captured["candidates"]] == ["cand-review-001"]


def test_seed_cmd_uses_snapshot_candidate_by_default(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import backend.scripts.hotpost.review_cards as mod

    candidate = _candidate()

    async def _fake_seed_from_candidate(item: CandidatePack, card_type: str):
        assert item.candidate_id == "cand-review-001"
        assert card_type == "validate"
        return SimpleNamespace(draft_id="draft-review-001")

    async def _unexpected_live_seed(*args, **kwargs):
        raise AssertionError("live seed path should not run")

    monkeypatch.setattr(mod, "get_snapshot_candidate", lambda candidate_id, snapshot_id=None: candidate)
    monkeypatch.setattr(mod, "seed_review_draft_from_candidate", _fake_seed_from_candidate)
    monkeypatch.setattr(mod, "seed_review_draft", _unexpected_live_seed)

    mod.seed_cmd(
        argparse.Namespace(
            candidate_id="cand-review-001",
            card_type="validate",
            snapshot_id="queue-20260411-abcd1234",
            live=False,
        )
    )

    assert capsys.readouterr().out.strip() == "draft-review-001"


def test_review_payload_keeps_empty_min_test_action_for_signal_draft() -> None:
    import backend.scripts.hotpost.review_cards as mod
    from app.services.hotpost.card_draft_builder import seed_validation_draft

    draft = seed_validation_draft(_candidate())
    payload = mod._review_payload(draft)

    assert payload["detail"]["min_test_action"] == ""
