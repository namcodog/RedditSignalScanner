from __future__ import annotations

import pytest

from app.schemas.hotpost_validate_details import HotValidationDetail
from app.services.hotpost.card_content_generator import build_backfill_draft
from app.services.hotpost.published_card_semantic_refresh import (
    merge_semantic_refresh,
    refresh_published_card_semantics,
    select_cards_for_semantic_refresh,
    semantic_change_summary,
)


def test_merge_semantic_refresh_updates_copy_and_preserves_publish_identity() -> None:
    original = _published_card("card-1", lane="signal")
    regenerated = {
        **_published_card("card-1", lane="breakdown"),
        "title": "新版标题",
        "summary_line": "新版摘要",
        "audience": "新版读者",
        "why_now": "新版为什么现在看",
        "published_at": "2099-01-01T00:00:00Z",
        "detail": {
            "pain_point": "新版痛点",
            "target_user_and_scene": "新版场景",
            "why_test_now": "新版证据判断",
            "min_test_action": "去看原始讨论",
            "continue_signal": "新版继续观察",
            "stop_signal": "新版停止条件",
        },
    }

    updated = merge_semantic_refresh(original, regenerated)

    assert updated["title"] == "新版标题"
    assert updated["summary_line"] == "新版摘要"
    assert updated["detail"]["pain_point"] == "新版痛点"
    assert "min_test_action" not in updated["detail"]
    assert updated["card_id"] == "card-1"
    assert updated["signal_id"] == "sig-card-1"
    assert updated["lane"] == "signal"
    assert updated["card_type"] == "validate"
    assert updated["category_id"] == "validate"
    assert updated["published_at"] == "2026-04-01T00:00:00Z"
    assert updated["source_module"] == original["source_module"]


def test_merge_semantic_refresh_reorders_preview_quote_only_when_source_set_matches() -> None:
    original = _published_card("card-1")
    regenerated = {
        **original,
        "preview_quote": original["quotes"][1],
        "quotes": [original["quotes"][1], original["quotes"][0]],
    }

    updated = merge_semantic_refresh(original, regenerated)

    assert updated["preview_quote"]["permalink"] == "https://reddit.test/q2"
    assert [quote["permalink"] for quote in updated["quotes"]] == [
        "https://reddit.test/q2",
        "https://reddit.test/q1",
    ]


def test_select_cards_for_semantic_refresh_filters_by_lane_and_limit() -> None:
    cards = [
        _published_card("card-1", lane="signal"),
        _published_card("card-2", lane="hot"),
        _published_card("card-3", lane="signal"),
    ]

    selected = select_cards_for_semantic_refresh(cards, lanes={"signal"}, limit=1)

    assert [card["card_id"] for card in selected] == ["card-1"]


def test_semantic_change_summary_reports_only_copy_changes() -> None:
    before = _published_card("card-1")
    after = merge_semantic_refresh(
        before,
        {
            **before,
            "title": "新版标题",
            "detail": {
                **before["detail"],
                "why_test_now": "新版证据判断",
            },
        },
    )

    summary = semantic_change_summary(before, after)

    assert set(summary) == {"title", "detail"}
    assert summary["detail"]["why_test_now"]["after"] == "新版证据判断"


def test_build_backfill_draft_preserves_hot_lane_and_normalizes_detail_shape() -> None:
    card = _published_card("card-hot-1", lane="hot")

    draft = build_backfill_draft(card)

    assert draft.lane == "hot"
    assert isinstance(draft.detail, HotValidationDetail)
    assert draft.detail.flashpoint == "旧痛点"
    assert draft.detail.fight_line == "旧场景"


def test_merge_semantic_refresh_normalizes_hot_detail_shape() -> None:
    original = _published_card("card-hot-2", lane="hot")
    regenerated = {
        **original,
        "detail": {
            "flashpoint": "新版火点",
            "fight_line": "新版争议线",
            "why_test_now": "新版证据判断",
            "continue_signal": "新版继续观察",
            "stop_signal": "新版停止条件",
        },
    }

    updated = merge_semantic_refresh(original, regenerated)

    assert updated["detail"] == {
        "flashpoint": "新版火点",
        "fight_line": "新版争议线",
        "why_test_now": "新版证据判断",
        "continue_signal": "新版继续观察",
        "stop_signal": "新版停止条件",
    }


def test_merge_semantic_refresh_preserves_breakdown_detail_shape() -> None:
    original = _published_write_card("card-write-1")
    regenerated = {
        **original,
        "detail": {
            "thesis": "新版判断",
            "writing_angle_or_perspective": "新版角度",
            "tension_point_or_why_it_matters": "新版张力",
            "title_hooks": ["hook-1"],
            "quote_pack": ["quote-1", "quote-2"],
        },
    }

    updated = merge_semantic_refresh(original, regenerated)

    assert updated["detail"] == regenerated["detail"]


@pytest.mark.asyncio
async def test_refresh_published_card_semantics_uses_breakdown_refresh_for_write_cards(monkeypatch: pytest.MonkeyPatch) -> None:
    original = _published_write_card("card-write-2")

    async def _fake_breakdown_refresh(_draft):
        draft = build_backfill_draft(original)
        return draft.model_copy(
            update={
                "title": "新版写卡标题",
                "summary_line": "新版写卡摘要",
                "detail": draft.detail.model_copy(update={"thesis": "新版判断"}),
            }
        )

    async def _boom(*_args, **_kwargs):
        raise AssertionError("write cards should not use validate refresh path")

    monkeypatch.setattr(
        "app.services.hotpost.published_card_semantic_refresh.refresh_breakdown_content",
        _fake_breakdown_refresh,
    )
    monkeypatch.setattr(
        "app.services.hotpost.published_card_semantic_refresh.generate_card_content",
        _boom,
    )

    updated = await refresh_published_card_semantics(original)

    assert updated["title"] == "新版写卡标题"
    assert updated["summary_line"] == "新版写卡摘要"
    assert updated["detail"]["thesis"] == "新版判断"


def _published_card(card_id: str, *, lane: str = "signal") -> dict:
    return {
        "card_id": card_id,
        "signal_id": f"sig-{card_id}",
        "card_type": "validate",
        "lane": lane,
        "category_id": "validate",
        "source_scope_id": "ai-automation",
        "source_scope_name": "AI 与自动化",
        "source_domain_id": "ai-automation",
        "source_domain_name": "AI 与自动化",
        "source_event_at": "2026-04-01T00:00:00Z",
        "title": "旧标题",
        "summary_line": "旧摘要",
        "audience": "旧读者",
        "why_now": "旧为什么现在看",
        "why_now_reason": "recurring_7d",
        "signal_level": "rising",
        "intent_tags": ["替换"],
        "top_community": "r/test",
        "thread_count": 1,
        "community_count": 1,
        "preview_quote": {
            "text": "quote one",
            "community": "r/test",
            "permalink": "https://reddit.test/q1",
        },
        "published_at": "2026-04-01T00:00:00Z",
        "source_module": {
            "primary_communities": ["r/test"],
            "top_community": "r/test",
            "tone_tags": [],
            "thread_count": 1,
            "community_count": 1,
            "last_active_text": "近7天",
        },
        "quotes": [
            {
                "text": "quote one",
                "community": "r/test",
                "permalink": "https://reddit.test/q1",
            },
            {
                "text": "quote two",
                "community": "r/test",
                "permalink": "https://reddit.test/q2",
            },
        ],
        "source_link": "https://reddit.test/q1",
        "detail": {
            "pain_point": "旧痛点",
            "target_user_and_scene": "旧场景",
            "why_test_now": "旧证据判断",
            "min_test_action": "去看原始讨论",
            "continue_signal": "旧继续观察",
            "stop_signal": "旧停止条件",
        },
    }


def _published_write_card(card_id: str) -> dict:
    card = _published_card(card_id, lane="breakdown")
    card["card_type"] = "write"
    card["category_id"] = "write"
    card["detail"] = {
        "thesis": "旧判断",
        "writing_angle_or_perspective": "旧角度",
        "tension_point_or_why_it_matters": "旧张力",
        "title_hooks": ["旧 hook"],
        "quote_pack": ["旧 quote"],
    }
    return card
