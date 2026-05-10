from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services.hotpost import mini_snapshot as mini_snapshot_module
from app.services.hotpost.mini_snapshot import build_mini_snapshot, publish_mini_snapshot
from app.services.hotpost.topic_tree_rolling_inventory import build_governed_rolling_inventory


def _sample_payload() -> dict:
    return {
        "categories": [
            {"category_id": "all", "title": "全部", "description": "全部卡片"},
            {"category_id": "validate", "title": "潜力快帖", "description": "快帖"},
        ],
        "candidates": [],
        "drafts": [],
        "published": [
            {
                "card_id": "card-hot",
                "signal_id": "signal-hot",
                "card_type": "validate",
                "lane": "hot",
                "category_id": "validate",
                "source_scope_id": "ai-automation",
                "source_scope_name": "AI 与自动化",
                "source_domain_id": "reddit",
                "source_domain_name": "Reddit",
                "source_event_at": "2026-04-08T12:00:00Z",
                "title": "Sam Altman 家遭枪击这帖火了，大家在吵这到底是治安事件，还是反 AI 情绪开始越线",
                "summary_line": "这帖真正吵起来的地方是：这到底只是富豪安保问题，还是反 AI 情绪已经开始从嘴上骂人走向线下威胁。",
                "audience": "围观 AI 风险的人",
                "why_now": "这波讨论已经不只是在聊案件本身，而是在争反 AI 情绪会不会继续外溢。",
                "why_now_reason": "recurring_7d",
                "signal_level": "hot",
                "intent_tags": ["舆情争议"],
                "source_module": {
                    "primary_communities": ["r/OpenAI"],
                    "top_community": "r/OpenAI",
                    "tone_tags": ["heated"],
                    "thread_count": 6,
                    "community_count": 2,
                    "last_active_text": "3h ago",
                },
                "preview_quote": {"text": "The Butlerian Jihad is starting early it seems", "community": "r/OpenAI", "permalink": "https://reddit.com/hot"},
                "quotes": [{"text": "The Butlerian Jihad is starting early it seems", "community": "r/OpenAI", "permalink": "https://reddit.com/hot"}],
                "source_link": "https://reddit.com/post-hot",
                "published_at": "2026-04-08T12:00:00Z",
                "detail": {
                    "flashpoint": "Sam Altman 住所接连遭袭的消息一出，评论区立刻把话题从单个治安事件拉到 AI 领袖是否正在成为现实攻击目标。",
                    "fight_line": "这到底是针对富人的普通治安事件，还是反 AI 情绪开始越过口水线，变成对 AI 领袖的现实威胁。",
                    "why_test_now": "关键证据是“Tax the rich for their own safety.”和“The Butlerian Jihad is starting early it seems”。讨论已经不是单纯同情受害者，而是在把这次枪击往“反 AI / 反科技富豪”方向解释。",
                    "continue_signal": "继续看后续是否出现更多把 AI 公司高管当成线下情绪出口的事件。",
                    "stop_signal": "如果后面只剩零散围观，没有更多具体事件，这条线索就先放下。",
                },
                "controversy_chart": {
                    "support_ratio": 0.45,
                    "oppose_ratio": 0.35,
                    "neutral_ratio": 0.2,
                    "support_point": "支持派把它看成富豪安保问题。",
                    "oppose_point": "反对派觉得反 AI 情绪已经开始越线。",
                    "neutral_point": "中立派还在等更多证据。",
                    "debate_focus": "这到底只是治安事件，还是反 AI 情绪线下化。",
                    "dominant_side": "support",
                    "confidence": "medium",
                },
                "controversy_meta": {
                    "post_id": "card-hot-post",
                    "sample_size": 12,
                    "sampled_at": "2026-04-08T12:00:00Z",
                    "fetch_status": "ok",
                    "llm_summary_version": "test",
                    "sample_quality": "medium",
                    "summary_status": "ok",
                },
            },
            {
                "card_id": "card-2",
                "signal_id": "signal-2",
                "card_type": "write",
                "category_id": "write",
                "source_scope_id": "ai-automation",
                "source_scope_name": "AI 与自动化",
                "source_domain_id": "reddit",
                "source_domain_name": "Reddit",
                "source_event_at": "2026-04-08T10:00:00Z",
                "title": "写作卡",
                "summary_line": "摘要 2",
                "audience": "团队",
                "why_now": "why 2",
                "why_now_reason": "recurring_7d",
                "signal_level": "hot",
                "intent_tags": ["趋势变化"],
                "source_module": {
                    "primary_communities": ["r/artificial"],
                    "top_community": "r/artificial",
                    "tone_tags": ["urgent"],
                    "thread_count": 2,
                    "community_count": 1,
                    "last_active_text": "2h ago",
                },
                "preview_quote": {"text": "quote2", "community": "r/artificial", "permalink": "https://reddit.com/2"},
                "quotes": [{"text": "quote2", "community": "r/artificial", "permalink": "https://reddit.com/2"}],
                "source_link": "https://reddit.com/post-2",
                "published_at": "2026-04-08T10:00:00Z",
                "detail": {
                    "thesis": "thesis",
                    "writing_angle_or_perspective": "angle",
                    "tension_point_or_why_it_matters": "tension",
                    "title_hooks": ["hook"],
                    "quote_pack": ["quote"],
                },
            },
            {
                "card_id": "card-1",
                "signal_id": "signal-1",
                "card_type": "validate",
                "category_id": "validate",
                "source_scope_id": "ai-automation",
                "source_scope_name": "AI 与自动化",
                "source_domain_id": "reddit",
                "source_domain_name": "Reddit",
                "source_event_at": "2026-04-07T10:00:00Z",
                "title": "大家不再只问赛道热不热",
                "summary_line": "摘要 1",
                "audience": "创始人",
                "why_now": "why 1",
                "why_now_reason": "recurring_7d",
                "signal_level": "rising",
                "intent_tags": ["效率工具"],
                "source_module": {
                    "primary_communities": ["r/codex"],
                    "top_community": "r/codex",
                    "tone_tags": ["friction"],
                    "thread_count": 3,
                    "community_count": 2,
                    "last_active_text": "1d ago",
                },
                "preview_quote": {"text": "quote1", "community": "r/codex", "permalink": "https://reddit.com/1"},
                "quotes": [{"text": "quote1", "community": "r/codex", "permalink": "https://reddit.com/1"}],
                "source_link": "https://reddit.com/post-1",
                "published_at": "2026-04-07T10:00:00Z",
                "detail": {
                    "pain_point": "pain",
                    "target_user_and_scene": "scene",
                    "why_test_now": "why now",
                    "min_test_action": "action",
                    "continue_signal": "如果接下来在更多社区里还出现同样抱怨，就继续盯",
                    "stop_signal": "如果后面只剩零散吐槽，没有新的具体场景或后续追问，就先放过",
                },
            },
        ],
    }


def _make_published_card(
    *,
    card_id: str,
    published_at: str,
    lane: str,
    source_link: str,
    title: str,
    source_scope_id: str = "ai-automation",
    named_topic_ids: list[str] | None = None,
    topic_pack_id: str | None = None,
    topic_cluster_id: str | None = None,
    top_community: str | None = None,
) -> dict:
    card_type = "write" if lane == "breakdown" else "validate"
    category_id = "write" if lane == "breakdown" else "validate"
    payload = {
        "card_id": card_id,
        "signal_id": f"signal-{card_id}",
        "card_type": card_type,
        "category_id": category_id,
        "lane": lane,
        "source_scope_id": source_scope_id,
        "source_scope_name": {
            "ai-automation": "AI 与自动化",
            "business-growth-ops": "商业增长与运营",
            "ecommerce-sellers": "电商与卖家",
        }.get(source_scope_id, source_scope_id),
        "source_domain_id": "reddit",
        "source_domain_name": "Reddit",
        "title": title,
        "summary_line": f"{title} 摘要",
        "audience": "团队",
        "why_now": f"{title} why_now",
        "source_link": source_link,
        "published_at": published_at,
        "named_topic_ids": named_topic_ids or [],
        "topic_pack_id": topic_pack_id,
        "topic_cluster_id": topic_cluster_id,
        "top_community": top_community,
    }
    if lane == "hot" and card_type == "validate":
        payload["controversy_chart"] = {
            "support_ratio": 0.4,
            "oppose_ratio": 0.35,
            "neutral_ratio": 0.25,
            "support_point": "支持派先看问题本身。",
            "oppose_point": "反对派已经开始强烈反弹。",
            "neutral_point": "中立派还在观察后续。",
            "debate_focus": f"{title} 的争议点",
            "dominant_side": "support",
            "confidence": "medium",
        }
        payload["controversy_meta"] = {
            "post_id": f"post-{card_id}",
            "sample_size": 10,
            "sampled_at": published_at,
            "fetch_status": "ok",
            "llm_summary_version": "test",
            "sample_quality": "medium",
            "summary_status": "ok",
        }
    return payload


def _homepage_shelf_payload() -> dict:
    lanes = [
        ("card-01", "signal", "https://reddit.com/signal-01", "signal 01"),
        ("card-02", "signal", "https://reddit.com/signal-02", "signal 02"),
        ("card-03", "hot", "https://reddit.com/hot-01", "hot 01"),
        ("card-04", "signal", "https://reddit.com/signal-04", "signal 04"),
        ("card-05", "breakdown", "https://reddit.com/breakdown-dup", "breakdown dup keep"),
        ("card-06", "signal", "https://reddit.com/signal-06", "signal 06"),
        ("card-07", "breakdown", "https://reddit.com/breakdown-dup", "breakdown dup drop"),
        ("card-08", "signal", "https://reddit.com/signal-08", "signal 08"),
        ("card-09", "breakdown", "https://reddit.com/breakdown-02", "breakdown 02"),
        ("card-10", "signal", "https://reddit.com/signal-10", "signal 10"),
        ("card-11", "signal", "https://reddit.com/signal-11", "signal 11"),
        ("card-12", "signal", "https://reddit.com/signal-12", "signal 12"),
        ("card-13", "signal", "https://reddit.com/signal-13", "signal 13"),
        ("card-14", "signal", "https://reddit.com/signal-14", "signal 14"),
        ("card-15", "signal", "https://reddit.com/signal-15", "signal 15"),
        ("card-16", "signal", "https://reddit.com/signal-16", "signal 16"),
        ("card-17", "signal", "https://reddit.com/signal-17", "signal 17"),
        ("card-18", "signal", "https://reddit.com/signal-18", "signal 18"),
        ("card-19", "signal", "https://reddit.com/signal-19", "signal 19"),
        ("card-20", "signal", "https://reddit.com/signal-20", "signal 20"),
        ("card-21", "signal", "https://reddit.com/signal-21", "signal 21"),
        ("card-22", "signal", "https://reddit.com/signal-22", "signal 22"),
        ("card-23", "signal", "https://reddit.com/signal-23", "signal 23"),
        ("card-24", "signal", "https://reddit.com/signal-24", "signal 24"),
        ("card-25", "signal", "https://reddit.com/signal-25", "signal 25"),
        ("card-26", "signal", "https://reddit.com/signal-26", "signal 26"),
        ("card-27", "breakdown", "https://reddit.com/breakdown-03", "breakdown 03"),
        ("card-28", "signal", "https://reddit.com/signal-28", "signal 28"),
        ("card-29", "signal", "https://reddit.com/signal-29", "signal 29"),
        ("card-30", "signal", "https://reddit.com/signal-30", "signal 30"),
        ("card-31", "breakdown", "https://reddit.com/breakdown-04", "breakdown 04"),
        ("card-32", "signal", "https://reddit.com/signal-32", "signal 32"),
        ("card-33", "breakdown", "https://reddit.com/breakdown-05", "breakdown 05"),
    ]
    published = [
        _make_published_card(
            card_id=card_id,
            published_at=f"2026-04-12T{34-index:02d}:00:00Z",
            lane=lane,
            source_link=source_link,
            title=title,
        )
        for index, (card_id, lane, source_link, title) in enumerate(lanes, start=1)
    ]
    return {
        "categories": [
            {"category_id": "all", "title": "全部", "description": "全部卡片"},
            {"category_id": "validate", "title": "潜力快帖", "description": "快帖"},
        ],
        "published": published,
    }


def _homepage_display_payload() -> dict:
    published = [
        _make_published_card(card_id="ai-hot-1", published_at="2026-04-13T15:00:00Z", lane="hot", source_link="https://reddit.com/ai-hot-1", title="AI hot 1", source_scope_id="ai-automation"),
        _make_published_card(card_id="bgo-breakdown-1", published_at="2026-04-13T14:50:00Z", lane="breakdown", source_link="https://reddit.com/bgo-breakdown-1", title="BGO breakdown 1", source_scope_id="business-growth-ops"),
        _make_published_card(card_id="ai-signal-1", published_at="2026-04-13T14:40:00Z", lane="signal", source_link="https://reddit.com/ai-signal-1", title="AI signal 1", source_scope_id="ai-automation"),
        _make_published_card(card_id="ai-signal-2", published_at="2026-04-13T14:30:00Z", lane="signal", source_link="https://reddit.com/ai-signal-2", title="AI signal 2", source_scope_id="ai-automation"),
        _make_published_card(card_id="ecom-signal-1", published_at="2026-04-13T14:20:00Z", lane="signal", source_link="https://reddit.com/ecom-signal-1", title="Ecom signal 1", source_scope_id="ecommerce-sellers"),
        _make_published_card(card_id="bgo-hot-1", published_at="2026-04-13T14:10:00Z", lane="hot", source_link="https://reddit.com/bgo-hot-1", title="BGO hot 1", source_scope_id="business-growth-ops"),
        _make_published_card(card_id="ecom-breakdown-1", published_at="2026-04-13T14:00:00Z", lane="breakdown", source_link="https://reddit.com/ecom-breakdown-1", title="Ecom breakdown 1", source_scope_id="ecommerce-sellers"),
        _make_published_card(card_id="bgo-signal-1", published_at="2026-04-13T13:50:00Z", lane="signal", source_link="https://reddit.com/bgo-signal-1", title="BGO signal 1", source_scope_id="business-growth-ops"),
        _make_published_card(card_id="ecom-signal-2", published_at="2026-04-13T13:40:00Z", lane="signal", source_link="https://reddit.com/ecom-signal-2", title="Ecom signal 2", source_scope_id="ecommerce-sellers"),
        _make_published_card(card_id="ai-hot-2", published_at="2026-04-13T13:30:00Z", lane="hot", source_link="https://reddit.com/ai-hot-2", title="AI hot 2", source_scope_id="ai-automation", named_topic_ids=["prompt-engineering"]),
        _make_published_card(card_id="bgo-signal-2", published_at="2026-04-13T13:20:00Z", lane="signal", source_link="https://reddit.com/bgo-signal-2", title="BGO signal 2", source_scope_id="business-growth-ops"),
        _make_published_card(card_id="ecom-signal-3", published_at="2026-04-13T13:10:00Z", lane="signal", source_link="https://reddit.com/ecom-signal-3", title="Ecom signal 3", source_scope_id="ecommerce-sellers"),
        _make_published_card(card_id="ai-signal-3", published_at="2026-04-13T13:00:00Z", lane="signal", source_link="https://reddit.com/ai-signal-3", title="AI signal 3", source_scope_id="ai-automation"),
        _make_published_card(card_id="bgo-hot-2", published_at="2026-04-13T12:50:00Z", lane="hot", source_link="https://reddit.com/bgo-hot-2", title="BGO hot 2", source_scope_id="business-growth-ops"),
        _make_published_card(card_id="ecom-breakdown-2", published_at="2026-04-13T12:40:00Z", lane="breakdown", source_link="https://reddit.com/ecom-breakdown-2", title="Ecom breakdown 2", source_scope_id="ecommerce-sellers"),
    ]
    return {
        "categories": [
            {"category_id": "all", "title": "全部", "description": "全部卡片"},
            {"category_id": "validate", "title": "潜力快帖", "description": "快帖"},
        ],
        "published": published,
    }


def _homepage_display_tail_run_payload() -> dict:
    published = [
        _make_published_card(card_id="hot-bgo-1", published_at="2026-04-13T15:00:00Z", lane="hot", source_link="https://reddit.com/hot-bgo-1", title="BGO hot 1", source_scope_id="business-growth-ops"),
        _make_published_card(card_id="hot-ai-1", published_at="2026-04-13T14:50:00Z", lane="hot", source_link="https://reddit.com/hot-ai-1", title="AI hot 1", source_scope_id="ai-automation"),
        _make_published_card(card_id="signal-ecom-1", published_at="2026-04-13T14:40:00Z", lane="signal", source_link="https://reddit.com/signal-ecom-1", title="Ecom signal 1", source_scope_id="ecommerce-sellers"),
        _make_published_card(card_id="signal-bgo-1", published_at="2026-04-13T14:30:00Z", lane="signal", source_link="https://reddit.com/signal-bgo-1", title="BGO signal 1", source_scope_id="business-growth-ops"),
        _make_published_card(card_id="breakdown-ecom-1", published_at="2026-04-13T14:20:00Z", lane="breakdown", source_link="https://reddit.com/breakdown-ecom-1", title="Ecom breakdown 1", source_scope_id="ecommerce-sellers"),
        _make_published_card(card_id="hot-bgo-2", published_at="2026-04-13T14:10:00Z", lane="hot", source_link="https://reddit.com/hot-bgo-2", title="BGO hot 2", source_scope_id="business-growth-ops"),
        _make_published_card(card_id="hot-ai-2", published_at="2026-04-13T14:00:00Z", lane="hot", source_link="https://reddit.com/hot-ai-2", title="AI hot 2", source_scope_id="ai-automation"),
        _make_published_card(card_id="signal-ecom-2", published_at="2026-04-13T13:50:00Z", lane="signal", source_link="https://reddit.com/signal-ecom-2", title="Ecom signal 2", source_scope_id="ecommerce-sellers"),
        _make_published_card(card_id="breakdown-bgo-1", published_at="2026-04-13T13:40:00Z", lane="breakdown", source_link="https://reddit.com/breakdown-bgo-1", title="BGO breakdown 1", source_scope_id="business-growth-ops"),
        _make_published_card(card_id="signal-ecom-3", published_at="2026-04-13T13:30:00Z", lane="signal", source_link="https://reddit.com/signal-ecom-3", title="Ecom signal 3", source_scope_id="ecommerce-sellers"),
        _make_published_card(card_id="signal-ecom-4", published_at="2026-04-13T13:20:00Z", lane="signal", source_link="https://reddit.com/signal-ecom-4", title="Ecom signal 4", source_scope_id="ecommerce-sellers"),
        _make_published_card(card_id="signal-bgo-2", published_at="2026-04-13T13:10:00Z", lane="signal", source_link="https://reddit.com/signal-bgo-2", title="BGO signal 2", source_scope_id="business-growth-ops"),
        _make_published_card(card_id="signal-ai-1", published_at="2026-04-13T13:00:00Z", lane="signal", source_link="https://reddit.com/signal-ai-1", title="AI signal 1", source_scope_id="ai-automation"),
        _make_published_card(card_id="signal-ai-2", published_at="2026-04-13T12:50:00Z", lane="signal", source_link="https://reddit.com/signal-ai-2", title="AI signal 2", source_scope_id="ai-automation"),
        _make_published_card(card_id="signal-ai-3", published_at="2026-04-13T12:40:00Z", lane="signal", source_link="https://reddit.com/signal-ai-3", title="AI signal 3", source_scope_id="ai-automation"),
    ]
    return {
        "categories": [
            {"category_id": "all", "title": "全部", "description": "全部卡片"},
            {"category_id": "validate", "title": "潜力快帖", "description": "快帖"},
        ],
        "published": published,
    }


def test_build_mini_snapshot_orders_cards_newest_first() -> None:
    snapshot = build_mini_snapshot(_sample_payload())
    assert snapshot["schema_version"] == "hotpost-mini-release/v1"
    assert snapshot["card_count"] == 3
    assert snapshot["feed_contract"] == {"initial_page_size": 30, "max_page_size": 30}
    assert [item["card_id"] for item in snapshot["cards"]] == ["card-hot", "card-2", "card-1"]
    assert snapshot["published_at"] == "2026-04-08T12:00:00Z"
    assert len(snapshot["checksum"]) == 40
    assert snapshot["cards"][0]["controversy_chart"]["debate_focus"] == "这到底只是治安事件，还是反 AI 情绪线下化。"
    assert "min_test_action" not in snapshot["cards"][2]["detail"]
    assert snapshot["cards"][2]["title"] == "大家不再只问赛道热不热"
    assert snapshot["cards"][2]["detail"]["continue_signal"] == "如果接下来在更多社区里还出现同样抱怨，就继续看。"
    assert snapshot["cards"][2]["detail"]["stop_signal"] == "如果后面只剩零散吐槽，没有新的具体场景或后续追问，就暂时不用太在意。"


def test_build_mini_snapshot_applies_homepage_shelf_mix_rules() -> None:
    snapshot = build_mini_snapshot(_homepage_shelf_payload())

    top_window = snapshot["cards"][:30]
    top_keys = {(item["source_link"], item["lane"]) for item in top_window}

    assert snapshot["card_count"] == 33
    assert top_window[0]["lane"] == "hot"
    assert len(top_keys) == len(top_window)
    assert top_window[0]["card_id"] == "card-03"
    assert "card-07" not in {item["card_id"] for item in top_window}


def test_build_mini_snapshot_applies_homepage_display_order_policy() -> None:
    snapshot = build_mini_snapshot(_homepage_display_payload())
    front15 = snapshot["cards"][:15]

    assert [item["lane"] for item in front15[:5]] == ["hot", "hot", "signal", "signal", "breakdown"]
    assert [item["lane"] for item in front15[:2]] == ["hot", "hot"]
    assert sum(1 for item in front15 if item["lane"] == "hot") == 4

    run_max = 1
    run = 1
    for previous, current in zip(front15, front15[1:]):
        if previous["source_scope_id"] == current["source_scope_id"]:
            run += 1
            run_max = max(run_max, run)
        else:
            run = 1
    assert run_max <= 2
    assert sum(1 for item in front15[:5] if item.get("named_topic_ids")) <= 1


def test_build_mini_snapshot_prioritizes_same_day_published_cards_before_older_inventory() -> None:
    categories = [
        {"category_id": "all", "title": "全部", "description": "全部卡片"},
        {"category_id": "validate", "title": "潜力快帖", "description": "快帖"},
        {"category_id": "write", "title": "跨区热议", "description": "写作卡"},
    ]
    today_cards = [
        _make_published_card(
            card_id="today-hot",
            published_at="2026-04-20T14:55:00Z",
            lane="hot",
            source_link="https://reddit.com/today-hot",
            title="today hot",
            source_scope_id="business-growth-ops",
        ),
        _make_published_card(
            card_id="today-signal-1",
            published_at="2026-04-20T14:54:00Z",
            lane="signal",
            source_link="https://reddit.com/today-signal-1",
            title="today signal 1",
            source_scope_id="ecommerce-sellers",
        ),
        _make_published_card(
            card_id="today-signal-2",
            published_at="2026-04-20T14:53:00Z",
            lane="signal",
            source_link="https://reddit.com/today-signal-2",
            title="today signal 2",
            source_scope_id="ai-automation",
        ),
    ]
    older_cards = [
        _make_published_card(
            card_id=f"older-{index:02d}",
            published_at=f"2026-04-19T{23 - (index % 12):02d}:{59 - (index % 50):02d}:00Z",
            lane="signal" if index % 5 else "breakdown",
            source_link=f"https://reddit.com/older-{index:02d}",
            title=f"older {index:02d}",
            source_scope_id=("ai-automation" if index % 3 == 0 else "business-growth-ops" if index % 3 == 1 else "ecommerce-sellers"),
        )
        for index in range(1, 55)
    ]

    snapshot = build_mini_snapshot(
        {"categories": categories, "published": [*today_cards, *older_cards]},
        reference_time=datetime(2026, 4, 20, 15, 0, tzinfo=timezone.utc),
    )
    main_cards = [card for card in snapshot["cards"] if str(card.get("surface_bucket") or "main") == "main"]
    main_ids = [str(card.get("card_id") or "") for card in main_cards]
    supplement_ids = {
        str(card.get("card_id") or "")
        for card in snapshot["cards"]
        if str(card.get("surface_bucket") or "") == "supplement"
    }

    assert main_ids[:3] == ["today-hot", "today-signal-1", "today-signal-2"]
    assert {"today-hot", "today-signal-1", "today-signal-2"}.issubset(set(main_ids))
    assert {"today-hot", "today-signal-1", "today-signal-2"}.isdisjoint(supplement_ids)
    assert snapshot["card_count"] == len(today_cards) + len(older_cards)


def test_build_mini_snapshot_repairs_tail_same_scope_run_without_breaking_front_pattern() -> None:
    snapshot = build_mini_snapshot(_homepage_display_tail_run_payload())
    front15 = snapshot["cards"][:15]

    assert [item["lane"] for item in front15[:5]] == ["hot", "hot", "signal", "signal", "breakdown"]
    assert [item["lane"] for item in front15[:2]] == ["hot", "hot"]
    assert sum(1 for item in front15 if item["lane"] == "hot") == 4

    front9_scopes = [item["source_scope_id"] for item in front15[:9]]
    assert all(front9_scopes[index] != front9_scopes[index - 1] for index in range(1, len(front9_scopes)))

    run_max = 1
    run = 1
    for previous, current in zip(front15, front15[1:]):
        if previous["source_scope_id"] == current["source_scope_id"]:
            run += 1
            run_max = max(run_max, run)
        else:
            run = 1
    assert run_max <= 2


def _governance_visible_payload() -> dict:
    published: list[dict] = []
    for index in range(1, 19):
        published.append(
            _make_published_card(
                card_id=f"growth-{index:02d}",
                published_at=f"2026-04-17T09:{59-index:02d}:00Z",
                lane="signal",
                source_link=f"https://reddit.com/growth-{index:02d}",
                title=f"Growth paid {index}",
                source_scope_id="business-growth-ops",
                topic_pack_id="paid-economics",
                topic_cluster_id="ads",
                top_community="r/FacebookAds" if index % 2 else "r/PPC",
            )
        )
    for index in range(1, 10):
        published.append(
            _make_published_card(
                card_id=f"ai-{index:02d}",
                published_at=f"2026-04-17T08:{59-index:02d}:00Z",
                lane="signal" if index > 2 else "hot",
                source_link=f"https://reddit.com/ai-{index:02d}",
                title=f"AI upstream {index}",
                source_scope_id="ai-automation",
                topic_pack_id="upstream-winds" if index <= 4 else "agent-builder",
                topic_cluster_id="model-platform-shifts" if index <= 4 else "agent-workflows",
                top_community="r/OpenAI" if index <= 4 else "r/LLM",
            )
        )
    for index in range(1, 10):
        published.append(
            _make_published_card(
                card_id=f"ecom-{index:02d}",
                published_at=f"2026-04-17T07:{59-index:02d}:00Z",
                lane="breakdown" if index <= 4 else "signal",
                source_link=f"https://reddit.com/ecom-{index:02d}",
                title=f"Ecom selection {index}",
                source_scope_id="ecommerce-sellers",
                topic_pack_id="selection-signals" if index <= 6 else "kill-signals",
                topic_cluster_id="seller-category-direction" if index <= 6 else "seller-stop-signals",
                top_community="r/BuyItForLife" if index <= 4 else "r/ecommerce",
            )
        )
    return {
        "categories": [
            {"category_id": "all", "title": "全部", "description": "全部卡片"},
            {"category_id": "validate", "title": "潜力快帖", "description": "快帖"},
        ],
        "published": published,
    }


def _rolling_inventory_payload() -> dict:
    published: list[dict] = []
    for index in range(1, 6):
        published.append(
            _make_published_card(
                card_id=f"old-growth-{index:02d}",
                published_at=f"2026-04-17T0{6-index}:00:00Z",
                lane="signal",
                source_link=f"https://reddit.com/old-growth-{index:02d}",
                title=f"Growth old {index}",
                source_scope_id="business-growth-ops",
                topic_pack_id="paid-economics",
                topic_cluster_id="ads-measurement",
                top_community="r/FacebookAds",
            )
            | {"source_event_at": "2026-04-10T00:00:00Z"}
        )
    published.extend(
        [
            _make_published_card(
                card_id="fresh-ai",
                published_at="2026-04-17T08:00:00Z",
                lane="signal",
                source_link="https://reddit.com/fresh-ai",
                title="AI fresh",
                source_scope_id="ai-automation",
                topic_pack_id="upstream-winds",
                topic_cluster_id="model-platform-shifts",
                top_community="r/OpenAI",
            ),
            _make_published_card(
                card_id="fresh-ecom",
                published_at="2026-04-17T07:50:00Z",
                lane="signal",
                source_link="https://reddit.com/fresh-ecom",
                title="Ecom fresh",
                source_scope_id="ecommerce-sellers",
                topic_pack_id="selection-signals",
                topic_cluster_id="seller-category-direction",
                top_community="r/shopify",
            ),
            _make_published_card(
                card_id="fresh-growth-new",
                published_at="2026-04-17T07:40:00Z",
                lane="signal",
                source_link="https://reddit.com/fresh-growth-new",
                title="Growth fresh new source",
                source_scope_id="business-growth-ops",
                topic_pack_id="organic-discovery",
                topic_cluster_id="search-distribution-shifts",
                top_community="r/juststart",
            ),
        ]
    )
    return {
        "categories": [
            {"category_id": "all", "title": "全部", "description": "全部卡片"},
            {"category_id": "validate", "title": "潜力快帖", "description": "快帖"},
        ],
        "published": published,
    }


def _rolling_inventory_balance_payload() -> list[dict]:
    published: list[dict] = []
    for index in range(1, 41):
        published.append(
            _make_published_card(
                card_id=f"growth-{index:02d}",
                published_at=f"2026-04-17T08:{59-(index % 50):02d}:00Z",
                lane="signal",
                source_link=f"https://reddit.com/growth-{index:02d}",
                title=f"Growth {index}",
                source_scope_id="business-growth-ops",
                topic_pack_id="paid-economics",
                topic_cluster_id="ads-measurement",
                top_community="r/FacebookAds",
            )
        )
    for index in range(1, 13):
        published.append(
            _make_published_card(
                card_id=f"ai-{index:02d}",
                published_at=f"2026-04-17T07:{59-(index % 50):02d}:00Z",
                lane="signal",
                source_link=f"https://reddit.com/ai-{index:02d}",
                title=f"AI {index}",
                source_scope_id="ai-automation",
                topic_pack_id="upstream-winds" if index <= 8 else "agent-builder",
                topic_cluster_id="model-platform-shifts" if index <= 8 else "agent-workflows",
                top_community="r/OpenAI" if index <= 6 else "r/LLM",
            )
        )
    for index in range(1, 13):
        published.append(
            _make_published_card(
                card_id=f"ecom-{index:02d}",
                published_at=f"2026-04-17T06:{59-(index % 50):02d}:00Z",
                lane="signal",
                source_link=f"https://reddit.com/ecom-{index:02d}",
                title=f"Ecom {index}",
                source_scope_id="ecommerce-sellers",
                topic_pack_id="selection-signals" if index <= 8 else "kill-signals",
                topic_cluster_id="seller-category-direction" if index <= 8 else "seller-stop-signals",
                top_community="r/shopify" if index <= 6 else "r/ecommerce",
            )
        )
    return published


def test_build_mini_snapshot_keeps_hot_front_without_cross_day_governance_mix() -> None:
    snapshot = build_mini_snapshot(_governance_visible_payload())
    front30 = snapshot["cards"][:30]

    scope_counts = {}
    community_counts = {}
    pack_counts = {}
    for card in front30:
        scope = str(card.get("source_scope_id") or "")
        community = str(card.get("top_community") or "")
        pack = str(card.get("topic_pack_id") or "")
        scope_counts[scope] = scope_counts.get(scope, 0) + 1
        community_counts[community] = community_counts.get(community, 0) + 1
        pack_counts[pack] = pack_counts.get(pack, 0) + 1

    assert [item["lane"] for item in front30[:2]] == ["hot", "hot"]
    assert all(scope_counts.get(scope_id, 0) > 0 for scope_id in ("ai-automation", "business-growth-ops", "ecommerce-sellers"))
    assert community_counts
    assert pack_counts


def test_build_governed_rolling_inventory_drops_stale_overweight_cards() -> None:
    reference_time = datetime(2026, 4, 17, 8, 30, tzinfo=timezone.utc)
    selected = build_governed_rolling_inventory(
        _rolling_inventory_payload()["published"],
        reference_time=reference_time,
    )
    selected_ids = {str(item.get("card_id") or "") for item in selected}

    assert "fresh-ai" in selected_ids
    assert "fresh-ecom" in selected_ids
    assert "fresh-growth-new" in selected_ids
    assert all(not card_id.startswith("old-growth-") for card_id in selected_ids)


def test_build_mini_snapshot_keeps_all_published_cards_visible() -> None:
    reference_time = datetime(2026, 4, 17, 8, 30, tzinfo=timezone.utc)
    published = _rolling_inventory_balance_payload()
    snapshot = build_mini_snapshot(
        {"categories": _rolling_inventory_payload()["categories"], "published": published},
        reference_time=reference_time,
    )

    assert snapshot["card_count"] == len(published)
    assert snapshot["main_card_count"] == len(published)
    assert snapshot["supplement_card_count"] == 0
    main_cards = [card for card in snapshot["cards"] if str(card.get("surface_bucket") or "main") == "main"]
    assert len(main_cards) == len(published)
    assert all(str(card.get("surface_bucket") or "") == "main" for card in snapshot["cards"])


def test_build_governed_rolling_inventory_rotates_recent_tail_cards_before_reusing_them(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    releases_dir = tmp_path / "releases"
    releases_dir.mkdir(parents=True)
    monkeypatch.setattr(
        "app.services.hotpost.topic_tree_rolling_inventory.RELEASES_DIR",
        releases_dir,
    )

    current_cards = [
        _make_published_card(
            card_id="front-ai",
            published_at="2026-04-17T09:00:00Z",
            lane="signal",
            source_link="https://reddit.com/front-ai",
            title="front ai",
            source_scope_id="ai-automation",
            topic_pack_id="upstream-winds",
            topic_cluster_id="models",
            top_community="r/OpenAI",
        ),
        _make_published_card(
            card_id="front-growth",
            published_at="2026-04-17T08:59:00Z",
            lane="signal",
            source_link="https://reddit.com/front-growth",
            title="front growth",
            source_scope_id="business-growth-ops",
            topic_pack_id="organic-discovery",
            topic_cluster_id="search",
            top_community="r/SEO",
        ),
        _make_published_card(
            card_id="tail-repeat-1",
            published_at="2026-04-17T08:58:00Z",
            lane="signal",
            source_link="https://reddit.com/tail-repeat-1",
            title="tail repeat 1",
            source_scope_id="ecommerce-sellers",
            topic_pack_id="selection-signals",
            topic_cluster_id="seller-category-direction",
            top_community="r/shopify",
        ),
        _make_published_card(
            card_id="tail-repeat-2",
            published_at="2026-04-17T08:57:00Z",
            lane="signal",
            source_link="https://reddit.com/tail-repeat-2",
            title="tail repeat 2",
            source_scope_id="ai-automation",
            topic_pack_id="agent-builder",
            topic_cluster_id="agent-workflows",
            top_community="r/LLM",
        ),
        _make_published_card(
            card_id="tail-alt-1",
            published_at="2026-04-17T08:56:00Z",
            lane="signal",
            source_link="https://reddit.com/tail-alt-1",
            title="tail alt 1",
            source_scope_id="business-growth-ops",
            topic_pack_id="funnel-conversion",
            topic_cluster_id="funnel",
            top_community="r/juststart",
        ),
        _make_published_card(
            card_id="tail-alt-2",
            published_at="2026-04-17T08:55:00Z",
            lane="signal",
            source_link="https://reddit.com/tail-alt-2",
            title="tail alt 2",
            source_scope_id="ecommerce-sellers",
            topic_pack_id="kill-signals",
            topic_cluster_id="seller-stop-signals",
            top_community="r/ecommerce",
        ),
    ]

    previous_release = {
        "release_id": "release-prev",
        "published_at": "2026-04-17T08:50:00Z",
        "cards": [
            current_cards[0],
            current_cards[1],
            current_cards[2],
            current_cards[3],
        ],
    }
    older_release = {
        "release_id": "release-older",
        "published_at": "2026-04-17T08:40:00Z",
        "cards": [
            current_cards[0],
            current_cards[1],
            current_cards[2],
            current_cards[3],
        ],
    }
    (releases_dir / "release-prev.json").write_text(json.dumps(previous_release, ensure_ascii=False, indent=2), encoding="utf-8")
    (releases_dir / "release-older.json").write_text(json.dumps(older_release, ensure_ascii=False, indent=2), encoding="utf-8")

    selected = build_governed_rolling_inventory(
        current_cards,
        max_cards=4,
        reference_time=datetime(2026, 4, 17, 9, 0, tzinfo=timezone.utc),
        previous_cards=previous_release["cards"],
        stable_front_window=2,
    )
    selected_ids = {str(item.get("card_id") or "") for item in selected}

    assert {"front-ai", "front-growth"}.issubset(selected_ids)
    assert "tail-alt-1" in selected_ids or "tail-alt-2" in selected_ids
    assert len({"tail-repeat-1", "tail-repeat-2"} & selected_ids) <= 1


def test_publish_mini_snapshot_writes_latest_and_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "mini_snapshots"
    bundle_dir = tmp_path / "mini_bundle"
    extra_bundle_dir = tmp_path / "mini_favorites_bundle"
    payload = _sample_payload()
    payload["published"][0].pop("controversy_chart", None)
    payload["published"][0].pop("controversy_meta", None)

    def _fake_refresh(cards: list[dict]) -> list[dict]:
        refreshed: list[dict] = []
        for item in cards:
            if item.get("card_id") != "card-hot":
                refreshed.append(item)
                continue
            refreshed.append(
                {
                    **item,
                    "controversy_chart": {
                        "support_ratio": 0.5,
                        "oppose_ratio": 0.3,
                        "neutral_ratio": 0.2,
                        "support_point": "支持派更愿意把它看成富豪安保问题。",
                        "oppose_point": "反对派觉得这已经是反 AI 情绪外溢。",
                        "neutral_point": "中立派还在等后续证据。",
                        "debate_focus": "这到底只是富豪安保问题，还是反 AI 情绪已经开始从嘴上骂人走向线下威胁。",
                        "dominant_side": "support",
                        "confidence": "medium",
                    },
                    "controversy_meta": {
                        "post_id": "1abc23d",
                        "sample_size": 24,
                        "sampled_at": "2026-04-14T12:00:00Z",
                        "fetch_status": "ok",
                        "llm_summary_version": "hot-controversy-v1",
                        "sample_quality": "medium",
                        "summary_status": "ok",
                    },
                }
            )
        return refreshed

    monkeypatch.setattr(
        mini_snapshot_module,
        "refresh_hot_controversy_cards_sync",
        _fake_refresh,
    )

    result = publish_mini_snapshot(
        output_dir=output_dir,
        bundle_dir=bundle_dir,
        bundle_dirs=[extra_bundle_dir],
        payload=payload,
        refresh_hot_controversy=True,
    )

    latest = json.loads((output_dir / "latest.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    versioned = json.loads((output_dir / "releases" / f"{result['release_id']}.json").read_text(encoding="utf-8"))
    bundled_latest = json.loads((bundle_dir / "latest.json").read_text(encoding="utf-8"))
    bundled_manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    bundled_versioned = json.loads((bundle_dir / "releases" / f"{result['release_id']}.json").read_text(encoding="utf-8"))
    extra_bundled_latest = json.loads((extra_bundle_dir / "latest.json").read_text(encoding="utf-8"))
    extra_bundled_manifest = json.loads((extra_bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    cloud_meta = json.loads((output_dir / "cloud_db" / "mini_release_meta.json").read_text(encoding="utf-8"))
    cloud_cards = json.loads((output_dir / "cloud_db" / "mini_release_cards.json").read_text(encoding="utf-8"))
    cloud_meta_jsonl = (output_dir / "cloud_db" / "mini_release_meta.jsonl").read_text(encoding="utf-8").strip().splitlines()
    cloud_cards_jsonl = (output_dir / "cloud_db" / "mini_release_cards.jsonl").read_text(encoding="utf-8").strip().splitlines()
    cloud_meta_import = (output_dir / "cloud_db" / "mini_release_meta.import.json").read_text(encoding="utf-8").strip().splitlines()
    cloud_cards_import = (output_dir / "cloud_db" / "mini_release_cards.import.json").read_text(encoding="utf-8").strip().splitlines()
    cloud_meta_wechat = (output_dir / "cloud_db" / "mini_release_meta.wechat-import.json").read_text(encoding="utf-8").strip().splitlines()
    cloud_cards_wechat = (output_dir / "cloud_db" / "mini_release_cards.wechat-import.json").read_text(encoding="utf-8").strip().splitlines()

    assert latest["release_id"] == result["release_id"]
    assert manifest["latest_release_id"] == result["release_id"]
    assert manifest["release_count"] == 1
    assert versioned["checksum"] == result["checksum"]
    assert bundled_latest["card_count"] == 3
    assert bundled_manifest["latest_release_id"] == result["release_id"]
    assert bundled_versioned["cards"][0]["card_id"] == "card-hot"
    assert extra_bundled_latest["card_count"] == 3
    assert extra_bundled_manifest["latest_release_id"] == result["release_id"]
    assert cloud_meta[0]["release_id"] == result["release_id"]
    assert cloud_meta[0]["feed_contract"] == {"initial_page_size": 30, "max_page_size": 30}
    assert len(cloud_cards) == 3
    assert cloud_cards[0]["release_id"] == result["release_id"]
    assert cloud_cards[0]["controversy_chart"]["debate_focus"] == "这到底只是富豪安保问题，还是反 AI 情绪已经开始从嘴上骂人走向线下威胁。"
    assert cloud_cards[0]["controversy_meta"]["sample_size"] == 24
    assert "min_test_action" not in cloud_cards[2]["detail"]
    assert len(cloud_meta_jsonl) == 1
    assert "_id" not in json.loads(cloud_meta_jsonl[0])
    assert len(cloud_cards_jsonl) == 3
    assert json.loads(cloud_cards_jsonl[0])["release_id"] == result["release_id"]
    assert len(cloud_meta_import) == 1
    assert "_id" not in json.loads(cloud_meta_import[0])
    assert len(cloud_cards_import) == 3
    assert json.loads(cloud_cards_import[0])["release_id"] == result["release_id"]
    assert len(cloud_meta_wechat) == 1
    assert json.loads(cloud_meta_wechat[0])["_id"] == "latest"
    assert len(cloud_cards_wechat) == 3
    assert json.loads(cloud_cards_wechat[0])["release_id"] == result["release_id"]
    assert json.loads(cloud_cards_wechat[0])["_id"] == "card-hot"
    assert "min_test_action" not in json.loads(cloud_cards_wechat[2])["detail"]


def test_publish_mini_snapshot_bundle_manifest_excludes_removed_releases(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "mini_snapshots"
    bundle_dir = tmp_path / "mini_bundle"
    stale_release_dir = bundle_dir / "releases"
    stale_release_dir.mkdir(parents=True)
    (stale_release_dir / "release-stale.json").write_text(
        json.dumps(
            {
                "release_id": "release-stale",
                "checksum": "stale",
                "card_count": 0,
                "published_at": "2026-04-01T00:00:00Z",
                "cards": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = publish_mini_snapshot(
        output_dir=output_dir,
        bundle_dir=bundle_dir,
        payload=_sample_payload(),
    )

    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    release_paths = [entry["path"] for entry in manifest["releases"]]

    assert manifest["release_count"] == 1
    assert release_paths == [f"releases/{result['release_id']}.json"]
    for release_path in release_paths:
        assert (bundle_dir / release_path).exists()


def test_publish_mini_snapshot_reuses_release_id_when_checksum_is_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "mini_snapshots"

    def _fake_refresh(cards: list[dict]) -> list[dict]:
        refreshed: list[dict] = []
        for item in cards:
            if item.get("card_id") != "card-hot":
                refreshed.append(item)
                continue
            refreshed.append(
                {
                    **item,
                    "controversy_chart": {
                        "support_ratio": 0.5,
                        "oppose_ratio": 0.3,
                        "neutral_ratio": 0.2,
                        "support_point": "支持派更愿意把它看成富豪安保问题。",
                        "oppose_point": "反对派觉得这已经是反 AI 情绪外溢。",
                        "neutral_point": "中立派还在等后续证据。",
                        "debate_focus": "这到底只是富豪安保问题，还是反 AI 情绪已经开始从嘴上骂人走向线下威胁。",
                        "dominant_side": "support",
                        "confidence": "medium",
                    },
                    "controversy_meta": {
                        "post_id": "1abc23d",
                        "sample_size": 24,
                        "sampled_at": "2026-04-14T12:00:00Z",
                        "fetch_status": "ok",
                        "llm_summary_version": "hot-controversy-v1",
                        "sample_quality": "medium",
                        "summary_status": "ok",
                    },
                }
            )
        return refreshed

    monkeypatch.setattr(
        mini_snapshot_module,
        "refresh_hot_controversy_cards_sync",
        _fake_refresh,
    )

    first = publish_mini_snapshot(
        output_dir=output_dir,
        payload=_sample_payload(),
        refresh_hot_controversy=True,
    )
    second = publish_mini_snapshot(
        output_dir=output_dir,
        payload=_sample_payload(),
        refresh_hot_controversy=True,
    )

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

    assert first["release_id"] == second["release_id"]
    assert manifest["release_count"] == 1


def test_publish_mini_snapshot_skips_hot_refresh_when_all_hot_cards_are_already_enriched(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "mini_snapshots"
    payload = _sample_payload()
    payload["published"][0]["controversy_chart"] = {
        "support_ratio": 0.5,
        "oppose_ratio": 0.3,
        "neutral_ratio": 0.2,
        "support_point": "支持派更愿意把它看成富豪安保问题。",
        "oppose_point": "反对派觉得这已经是反 AI 情绪外溢。",
        "neutral_point": "中立派还在等后续证据。",
        "debate_focus": "这到底只是富豪安保问题，还是反 AI 情绪已经开始从嘴上骂人走向线下威胁。",
        "dominant_side": "support",
        "confidence": "medium",
    }
    payload["published"][0]["controversy_meta"] = {
        "post_id": "1abc23d",
        "sample_size": 24,
        "sampled_at": "2026-04-14T12:00:00Z",
        "fetch_status": "ok",
        "llm_summary_version": "hot-controversy-v1",
        "sample_quality": "medium",
        "summary_status": "ok",
    }

    def _unexpected_refresh(cards: list[dict]) -> list[dict]:
        raise AssertionError("hot controversy refresh should not run when all hot cards are already enriched")

    monkeypatch.setattr(
        mini_snapshot_module,
        "refresh_hot_controversy_cards_sync",
        _unexpected_refresh,
    )

    result = publish_mini_snapshot(
        output_dir=output_dir,
        payload=payload,
        refresh_hot_controversy=True,
    )
    latest = json.loads((output_dir / "latest.json").read_text(encoding="utf-8"))

    assert latest["release_id"] == result["release_id"]
    assert latest["cards"][0]["controversy_meta"]["sample_size"] == 24


def test_publish_mini_snapshot_skips_hot_refresh_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "mini_snapshots"

    def _unexpected_refresh(cards: list[dict]) -> list[dict]:
        raise AssertionError("hot controversy refresh should be opt-in")

    monkeypatch.setattr(
        mini_snapshot_module,
        "refresh_hot_controversy_cards_sync",
        _unexpected_refresh,
    )

    result = publish_mini_snapshot(output_dir=output_dir, payload=_sample_payload())
    latest = json.loads((output_dir / "latest.json").read_text(encoding="utf-8"))

    assert latest["release_id"] == result["release_id"]
    assert latest["cards"][0]["card_id"] == "card-hot"
    assert latest["cards"][0]["controversy_chart"]["debate_focus"] == "这到底只是治安事件，还是反 AI 情绪线下化。"
