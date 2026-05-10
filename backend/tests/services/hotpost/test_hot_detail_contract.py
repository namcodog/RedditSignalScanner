from __future__ import annotations

from app.services.hotpost.card_content_rules_config import load_card_content_rules


def _legacy_hot_card() -> dict:
    return {
        "card_id": "card-hot-legacy-001",
        "signal_id": "sig-hot-legacy-001",
        "card_type": "validate",
        "lane": "hot",
        "category_id": "validate",
        "source_scope_id": "business-growth-ops",
        "source_scope_name": "商业增长与运营",
        "source_domain_id": "business-growth-ops",
        "source_domain_name": "商业增长与运营",
        "source_event_at": "2026-04-10T00:00:00Z",
        "title": "Legacy hot card",
        "summary_line": "summary",
        "audience": "投手",
        "why_now": "why now",
        "why_now_reason": "new_threads_24h",
        "signal_level": "hot",
        "intent_tags": ["趋势变化"],
        "top_community": "r/PPC",
        "thread_count": 1,
        "community_count": 1,
        "preview_quote": {
            "text": "quote",
            "community": "r/PPC",
            "permalink": "https://www.reddit.com/r/PPC/comments/legacy/q1",
        },
        "published_at": "2026-04-10T00:00:00Z",
        "source_module": {
            "primary_communities": ["r/PPC"],
            "top_community": "r/PPC",
            "tone_tags": [],
            "thread_count": 1,
            "community_count": 1,
            "last_active_text": "1天前",
        },
        "quotes": [
            {
                "text": "quote",
                "community": "r/PPC",
                "permalink": "https://www.reddit.com/r/PPC/comments/legacy/q1",
            }
        ],
        "source_link": "https://www.reddit.com/r/PPC/comments/legacy",
        "detail": {
            "pain_point": "老 hot 卡还在沿用 signal 的旧字段。",
            "target_user_and_scene": "评论区已经从围观变成站队。",
            "why_test_now": "关键证据是开始站队。",
            "continue_signal": "继续看更多团队怎么站队。",
            "stop_signal": "如果后面只剩重复转述，就先放过。",
        },
    }


def _current_hot_card_with_controversy_meta() -> dict:
    return {
        **_legacy_hot_card(),
        "card_id": "card-hot-current-001",
        "controversy_chart": {
            "support_ratio": 0.21,
            "oppose_ratio": 0.5,
            "neutral_ratio": 0.29,
            "support_point": "先看能不能少手动维护。",
            "oppose_point": "这只是富豪的安保问题，不是反人工智能情绪失控。",
            "neutral_point": "还得看这次事件会不会影响人工智能的正常发展。",
            "debate_focus": "这到底只是治安事件还是反人工智能情绪越线了？",
            "dominant_side": "oppose",
            "confidence": "high",
        },
        "controversy_meta": {
            "post_id": "1sk82sc",
            "sample_size": 36,
            "sampled_at": "2026-04-14T07:25:00.957386Z",
            "fetch_status": "ok",
            "llm_summary_version": "cn_human_point_slots_v8",
            "sample_quality": "high",
            "summary_status": "ok",
            "confidence_reason": "判断相对保守。",
        },
    }


def test_get_card_detail_normalizes_legacy_hot_detail_payload(monkeypatch) -> None:
    from app.services.hotpost import clues_catalog

    monkeypatch.setattr(clues_catalog, "load_published_cards", lambda: [_legacy_hot_card()])

    detail = clues_catalog.get_card_detail("card-hot-legacy-001")

    assert detail is not None
    assert detail.lane == "hot"
    assert detail.detail.model_dump() == {
        "flashpoint": "老 hot 卡还在沿用 signal 的旧字段。",
        "fight_line": "评论区已经从围观变成站队。",
        "why_test_now": "关键证据是开始站队。",
        "continue_signal": "继续看更多团队怎么站队。",
        "stop_signal": "如果后面只剩重复转述，就先放过。",
    }


def test_get_card_detail_accepts_current_hot_controversy_meta(monkeypatch) -> None:
    from app.services.hotpost import clues_catalog

    monkeypatch.setattr(clues_catalog, "load_published_cards", lambda: [_current_hot_card_with_controversy_meta()])

    detail = clues_catalog.get_card_detail("card-hot-current-001")

    assert detail is not None
    assert detail.lane == "hot"
    assert detail.controversy_chart is not None
    assert detail.controversy_meta is not None
    assert detail.controversy_meta.sample_size == 36
    assert detail.controversy_meta.llm_summary_version == "cn_human_point_slots_v8"


def test_clean_detail_copy_supports_hot_detail_fields() -> None:
    from app.services.hotpost.mini_snapshot import _clean_detail_copy

    detail = {
        "flashpoint": "这帖突然炸起来",
        "fight_line": "评论区已经开始站队",
        "why_test_now": "关键证据就是那句 still works at all",
        "continue_signal": "继续看 answer engines",
        "stop_signal": "如果后面只剩转述就先放过",
    }

    _clean_detail_copy(detail, rules=load_card_content_rules())

    assert detail["flashpoint"].endswith("。")
    assert detail["fight_line"].endswith("。")
    assert detail["why_test_now"].endswith("。")
