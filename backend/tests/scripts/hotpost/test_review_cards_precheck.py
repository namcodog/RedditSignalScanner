from __future__ import annotations

import pytest

from app.schemas.hotpost_card_candidates import CandidatePack


def _candidate() -> CandidatePack:
    return CandidatePack.model_validate(
        {
            "candidate_id": "cand-review-precheck-001",
            "signal_id": "sig-review-precheck-001",
            "source_scope_id": "business-growth-ops",
            "source_scope_name": "商业增长与运营",
            "topic_pack_id": "paid-economics",
            "query": "lead quality",
            "matched_subreddit": "PPC",
            "post_id": "post-review-precheck-001",
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
                    "permalink": "https://www.reddit.com/r/PPC/comments/post-review-precheck-001/q1",
                }
            ],
        }
    )


def test_review_payload_includes_saved_precheck(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.scripts.hotpost.review_cards as mod
    from app.services.hotpost.card_draft_builder import seed_validation_draft

    draft = seed_validation_draft(_candidate())
    monkeypatch.setattr(
        mod,
        "load_draft_precheck",
        lambda draft_id: {
            "draft_id": draft_id,
            "decision": "PASS",
            "reasons": ["证据支撑当前主张"],
        },
    )

    payload = mod._review_payload(draft)

    assert payload["precheck"]["decision"] == "PASS"


def test_review_payload_includes_generation_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.scripts.hotpost.review_cards as mod
    from app.services.hotpost.card_draft_builder import seed_validation_draft

    draft = seed_validation_draft(_candidate())
    monkeypatch.setattr(mod, "load_draft_precheck", lambda draft_id: None)
    monkeypatch.setattr(
        mod,
        "load_generation_trace",
        lambda draft_id: {
            "draft_id": draft_id,
            "overall_status": "completed",
            "allow_breakdown": False,
        },
    )

    payload = mod._review_payload(draft)

    assert payload["generation_trace"]["overall_status"] == "completed"
    assert payload["generation_trace"]["allow_breakdown"] is False


def test_publish_cmd_blocks_precheck_block_without_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import argparse

    import backend.scripts.hotpost.review_cards as mod

    monkeypatch.setattr(
        mod,
        "load_draft_precheck",
        lambda draft_id: {"decision": "BLOCK", "reasons": ["证据不支撑标题"]},
    )

    def _unexpected_publish(*args, **kwargs):
        raise AssertionError("blocked draft should not publish")

    monkeypatch.setattr(mod, "publish_draft", _unexpected_publish)

    with pytest.raises(SystemExit, match="precheck BLOCK"):
        mod.publish_cmd(
            argparse.Namespace(
                draft_id="draft-blocked-001",
                override_precheck_block=False,
            )
        )


def test_publish_cmd_allows_precheck_block_with_override(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import argparse

    import backend.scripts.hotpost.review_cards as mod

    monkeypatch.setattr(
        mod,
        "load_draft_precheck",
        lambda draft_id: {"decision": "BLOCK", "reasons": ["证据不支撑标题"]},
    )
    monkeypatch.setattr(mod, "publish_draft", lambda draft_id, **kwargs: ("card-001", 12))

    mod.publish_cmd(
        argparse.Namespace(
            draft_id="draft-blocked-001",
            override_precheck_block=True,
        )
    )

    assert '"card_id": "card-001"' in capsys.readouterr().out
