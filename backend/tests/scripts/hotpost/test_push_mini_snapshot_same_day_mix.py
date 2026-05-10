from __future__ import annotations

from datetime import datetime, timezone

from app.services.hotpost.mini_snapshot import build_mini_snapshot

from .test_push_mini_snapshot import _make_published_card


def test_build_mini_snapshot_same_day_priority_still_mixes_without_breakdown() -> None:
    categories = [
        {"category_id": "all", "title": "全部", "description": "全部卡片"},
        {"category_id": "validate", "title": "潜力快帖", "description": "快帖"},
    ]
    same_day_cards = [
        _make_published_card(
            card_id="hot-01",
            published_at="2026-04-20T16:12:00Z",
            lane="hot",
            source_link="https://reddit.com/hot-01",
            title="hot 01",
            source_scope_id="ecommerce-sellers",
        ),
        _make_published_card(
            card_id="hot-02",
            published_at="2026-04-20T16:11:00Z",
            lane="hot",
            source_link="https://reddit.com/hot-02",
            title="hot 02",
            source_scope_id="business-growth-ops",
        ),
        _make_published_card(
            card_id="hot-03",
            published_at="2026-04-20T16:10:00Z",
            lane="hot",
            source_link="https://reddit.com/hot-03",
            title="hot 03",
            source_scope_id="ai-automation",
        ),
        _make_published_card(
            card_id="hot-04",
            published_at="2026-04-20T16:09:00Z",
            lane="hot",
            source_link="https://reddit.com/hot-04",
            title="hot 04",
            source_scope_id="ecommerce-sellers",
        ),
        _make_published_card(
            card_id="signal-01",
            published_at="2026-04-20T16:08:00Z",
            lane="signal",
            source_link="https://reddit.com/signal-01",
            title="signal 01",
            source_scope_id="business-growth-ops",
        ),
        _make_published_card(
            card_id="signal-02",
            published_at="2026-04-20T16:07:00Z",
            lane="signal",
            source_link="https://reddit.com/signal-02",
            title="signal 02",
            source_scope_id="ai-automation",
        ),
        _make_published_card(
            card_id="signal-03",
            published_at="2026-04-20T16:06:00Z",
            lane="signal",
            source_link="https://reddit.com/signal-03",
            title="signal 03",
            source_scope_id="ecommerce-sellers",
        ),
        _make_published_card(
            card_id="signal-04",
            published_at="2026-04-20T16:05:00Z",
            lane="signal",
            source_link="https://reddit.com/signal-04",
            title="signal 04",
            source_scope_id="business-growth-ops",
        ),
    ]

    snapshot = build_mini_snapshot(
        {"categories": categories, "published": same_day_cards},
        reference_time=datetime(2026, 4, 20, 16, 12, tzinfo=timezone.utc),
    )
    front8 = snapshot["cards"][:8]
    front8_lanes = [item["lane"] for item in front8]

    assert front8_lanes[:4] == ["hot", "hot", "signal", "signal"]
    assert front8_lanes.count("signal") >= 4


def test_build_mini_snapshot_keeps_single_lane_same_day_block_before_older_cards() -> None:
    categories = [
        {"category_id": "all", "title": "全部", "description": "全部卡片"},
        {"category_id": "validate", "title": "潜力快帖", "description": "快帖"},
    ]
    same_day_hot_cards = [
        _make_published_card(
            card_id=f"today-hot-{index:02d}",
            published_at=f"2026-04-20T16:{59-index:02d}:00Z",
            lane="hot",
            source_link=f"https://reddit.com/today-hot-{index:02d}",
            title=f"today hot {index:02d}",
            source_scope_id=("ai-automation" if index % 3 == 0 else "business-growth-ops" if index % 3 == 1 else "ecommerce-sellers"),
        )
        for index in range(1, 10)
    ]
    older_mixed_cards = [
        _make_published_card(
            card_id=f"older-signal-{index:02d}",
            published_at=f"2026-04-19T15:{59-index:02d}:00Z",
            lane="signal",
            source_link=f"https://reddit.com/older-signal-{index:02d}",
            title=f"older signal {index:02d}",
            source_scope_id=("ai-automation" if index % 2 else "business-growth-ops"),
        )
        for index in range(1, 6)
    ] + [
        _make_published_card(
            card_id=f"older-breakdown-{index:02d}",
            published_at=f"2026-04-19T14:{59-index:02d}:00Z",
            lane="breakdown",
            source_link=f"https://reddit.com/older-breakdown-{index:02d}",
            title=f"older breakdown {index:02d}",
            source_scope_id=("ecommerce-sellers" if index % 2 else "ai-automation"),
        )
        for index in range(1, 4)
    ]

    snapshot = build_mini_snapshot(
        {"categories": categories, "published": [*same_day_hot_cards, *older_mixed_cards]},
        reference_time=datetime(2026, 4, 20, 17, 0, tzinfo=timezone.utc),
    )
    ordered_ids = [item["card_id"] for item in snapshot["cards"]]
    front9_lanes = [item["lane"] for item in snapshot["cards"][:9]]

    assert front9_lanes == ["hot"] * len(same_day_hot_cards)
    assert all(ordered_ids.index(item["card_id"]) < len(same_day_hot_cards) for item in same_day_hot_cards)
    assert all(ordered_ids.index(item["card_id"]) >= len(same_day_hot_cards) for item in older_mixed_cards)


def test_build_mini_snapshot_promotes_same_day_breakdown_into_front_window() -> None:
    categories = [
        {"category_id": "all", "title": "全部", "description": "全部卡片"},
        {"category_id": "validate", "title": "潜力快帖", "description": "快帖"},
    ]
    same_day_hot_signal_cards = [
        _make_published_card(
            card_id=f"today-hot-{index:02d}",
            published_at=f"2026-04-20T16:{59-index:02d}:00Z",
            lane="hot",
            source_link=f"https://reddit.com/today-hot-{index:02d}",
            title=f"today hot {index:02d}",
            source_scope_id=("ai-automation" if index % 3 == 0 else "business-growth-ops" if index % 3 == 1 else "ecommerce-sellers"),
        )
        for index in range(1, 21)
    ] + [
        _make_published_card(
            card_id=f"today-signal-{index:02d}",
            published_at=f"2026-04-20T15:{59-index:02d}:00Z",
            lane="signal",
            source_link=f"https://reddit.com/today-signal-{index:02d}",
            title=f"today signal {index:02d}",
            source_scope_id=("ai-automation" if index % 3 == 0 else "business-growth-ops" if index % 3 == 1 else "ecommerce-sellers"),
        )
        for index in range(1, 21)
    ]
    same_day_breakdown_cards = [
        _make_published_card(
            card_id=f"today-breakdown-{index:02d}",
            published_at=f"2026-04-20T09:{59-index:02d}:00Z",
            lane="breakdown",
            source_link=f"https://reddit.com/today-breakdown-{index:02d}",
            title=f"today breakdown {index:02d}",
            source_scope_id=("ai-automation" if index % 2 else "business-growth-ops"),
        )
        for index in range(1, 4)
    ]
    older_cards = [
        _make_published_card(
            card_id=f"older-signal-{index:02d}",
            published_at=f"2026-04-19T12:{59-index:02d}:00Z",
            lane="signal",
            source_link=f"https://reddit.com/older-signal-{index:02d}",
            title=f"older signal {index:02d}",
            source_scope_id=("ai-automation" if index % 2 else "business-growth-ops"),
        )
        for index in range(1, 6)
    ]

    snapshot = build_mini_snapshot(
        {"categories": categories, "published": [*same_day_hot_signal_cards, *same_day_breakdown_cards, *older_cards]},
        reference_time=datetime(2026, 4, 20, 17, 0, tzinfo=timezone.utc),
    )
    front30 = snapshot["cards"][:30]

    assert any(item["lane"] == "breakdown" for item in front30)
    assert {item["card_id"] for item in same_day_breakdown_cards}.issubset({item["card_id"] for item in snapshot["cards"]})


def _max_lane_run(lanes: list[str]) -> int:
    max_run = 0
    current_lane = ""
    current_run = 0
    for lane in lanes:
        if lane == current_lane:
            current_run += 1
        else:
            current_lane = lane
            current_run = 1
        max_run = max(max_run, current_run)
    return max_run
