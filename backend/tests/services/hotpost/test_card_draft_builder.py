from __future__ import annotations

from app.schemas.hotpost_card_drafts import ValidationCardDraft
from app.services.hotpost.card_draft_builder import build_published_card


def _hot_draft() -> ValidationCardDraft:
    return ValidationCardDraft.model_validate(
        {
            "draft_id": "draft-hot",
            "candidate_id": "cand-hot",
            "candidate_ids": ["cand-hot"],
            "card_id": "card-hot",
            "signal_id": "sig-hot",
            "card_type": "validate",
            "lane": "hot",
            "category_id": "validate",
            "title": "Hot card",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "matched_subreddit": "LocalLLaMA",
            "post_id": "abc123",
            "score": 10,
            "num_comments": 5,
            "time_window": "24h",
            "signal_level": "hot",
            "why_now_reason": "new_threads_24h",
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 1,
            "evidence_quotes": [
                {
                    "text": "The modular boundary is useful, but switching tools takes work.",
                    "community": "r/LocalLLaMA",
                    "permalink": "https://www.reddit.com/r/LocalLLaMA/comments/abc123/x",
                }
            ],
            "summary_line": "A local agent framework drew interest, but migration cost is the debate.",
            "audience": "本地 LLM 开发者",
            "why_now": "Local agent tools are competing on control and switching cost.",
            "source_link": "https://www.reddit.com/r/LocalLLaMA/comments/abc123",
            "source_links": ["https://www.reddit.com/r/LocalLLaMA/comments/abc123"],
            "source_communities": ["r/LocalLLaMA"],
            "detail": {
                "flashpoint": "A new framework claims modular control.",
                "fight_line": "Some users want permissions; others see migration cost.",
                "why_test_now": "The comments compare control with tool fatigue.",
                "continue_signal": "Watch for migration reports.",
                "stop_signal": "Drop it if no real usage appears.",
            },
        }
    )


def test_build_published_hot_card_drops_internal_controversy_trace(monkeypatch) -> None:
    def _fake_refresh(cards):
        return [
            {
                **cards[0],
                "controversy_chart": {
                    "support_ratio": 0.4,
                    "oppose_ratio": 0.4,
                    "neutral_ratio": 0.2,
                    "support_point": "Modular permissions are useful.",
                    "oppose_point": "Switching tools is too costly.",
                    "neutral_point": "Needs real usage reports.",
                    "debate_focus": "Does control outweigh migration cost?",
                    "dominant_side": "neutral",
                    "confidence": "medium",
                },
                "controversy_meta": {
                    "post_id": "abc123",
                    "sample_size": 5,
                    "fetch_status": "ok",
                    "llm_summary_version": "cn_human_point_slots_v8",
                    "sample_quality": "medium",
                    "summary_status": "ok",
                    "llm_trace": {"stage": "hot_controversy", "status": "completed"},
                },
            }
        ]

    monkeypatch.setattr(
        "app.services.hotpost.card_draft_builder.refresh_hot_controversy_cards_sync",
        _fake_refresh,
    )

    card = build_published_card(_hot_draft())

    assert card.controversy_meta is not None
    assert "llm_trace" not in card.controversy_meta.model_dump()
