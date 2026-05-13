from __future__ import annotations


def test_build_mini_snapshot_rejects_hot_card_without_controversy_chart() -> None:
    from app.services.hotpost.mini_snapshot import build_mini_snapshot

    payload = {
        "categories": [{"category_id": "all", "title": "全部", "description": "全部卡片"}],
        "published": [
            {
                "card_id": "card-hot-1",
                "signal_id": "sig-hot-1",
                "card_type": "validate",
                "lane": "hot",
                "category_id": "validate",
                "source_scope_id": "business-growth-ops",
                "source_scope_name": "商业增长与运营",
                "source_domain_id": "business-growth-ops",
                "source_domain_name": "商业增长与运营",
                "source_event_at": "2026-04-16T00:00:00Z",
                "title": "hot card",
                "summary_line": "summary",
                "audience": "卖家",
                "why_now": "现在就在吵。",
                "why_now_reason": "new_threads_24h",
                "signal_level": "rising",
                "intent_tags": ["趋势变化"],
                "top_community": "r/ecommerce",
                "thread_count": 1,
                "community_count": 1,
                "source_module": {
                    "primary_communities": ["r/ecommerce"],
                    "top_community": "r/ecommerce",
                    "tone_tags": [],
                    "thread_count": 1,
                    "community_count": 1,
                    "last_active_text": "近24小时",
                },
                "preview_quote": {
                    "text": "quote",
                    "community": "r/ecommerce",
                    "permalink": "https://www.reddit.com/r/ecommerce/comments/post-hot/q1",
                },
                "published_at": "2026-04-16T01:00:00Z",
                "quotes": [
                    {
                        "text": "quote",
                        "community": "r/ecommerce",
                        "permalink": "https://www.reddit.com/r/ecommerce/comments/post-hot/q1",
                    }
                ],
                "source_link": "https://www.reddit.com/r/ecommerce/comments/post-hot",
                "detail": {
                    "flashpoint": "flashpoint",
                    "fight_line": "fight line",
                    "why_test_now": "why now",
                    "continue_signal": "continue",
                    "stop_signal": "stop",
                },
                "controversy_chart": None,
                "controversy_meta": None,
            }
        ],
    }

    try:
        build_mini_snapshot(payload)
    except ValueError as exc:
        assert "missing controversy chart" in str(exc)
        assert "card-hot-1" in str(exc)
    else:
        raise AssertionError("expected snapshot build to reject hot cards without controversy chart")


def test_build_mini_snapshot_keeps_all_published_cards_visible() -> None:
    from app.services.hotpost.mini_snapshot import build_mini_snapshot

    def _build_card(
        *,
        card_id: str,
        lane: str,
        source_event_at: str,
        published_at: str,
        source_link: str,
        title: str,
    ) -> dict:
        card = {
            "card_id": card_id,
            "signal_id": f"sig-{card_id}",
            "card_type": "validate",
            "lane": lane,
            "category_id": "validate",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "source_domain_id": "ai-automation",
            "source_domain_name": "AI 与自动化",
            "source_event_at": source_event_at,
            "title": title,
            "summary_line": "summary",
            "audience": "工程师",
            "why_now": "why now",
            "why_now_reason": "new_threads_24h" if lane == "hot" else "recurring_7d",
            "signal_level": "hot" if lane == "hot" else "rising",
            "intent_tags": ["热点"] if lane == "hot" else ["补充"],
            "top_community": "r/ClaudeCode" if lane == "hot" else "r/LocalLLaMA",
            "thread_count": 1,
            "community_count": 1,
            "source_module": {
                "primary_communities": ["r/ClaudeCode" if lane == "hot" else "r/LocalLLaMA"],
                "top_community": "r/ClaudeCode" if lane == "hot" else "r/LocalLLaMA",
                "tone_tags": [],
                "thread_count": 1,
                "community_count": 1,
                "last_active_text": "近24小时" if lane == "hot" else "近15天",
            },
            "preview_quote": {
                "text": "quote",
                "community": "r/ClaudeCode" if lane == "hot" else "r/LocalLLaMA",
                "permalink": source_link,
            },
            "published_at": published_at,
            "quotes": [
                {
                    "text": "quote",
                    "community": "r/ClaudeCode" if lane == "hot" else "r/LocalLLaMA",
                    "permalink": source_link,
                }
            ],
            "source_link": source_link,
            "detail": {
                "flashpoint": "flash",
                "fight_line": "fight",
                "why_test_now": "why",
                "continue_signal": "continue",
                "stop_signal": "stop",
            }
            if lane == "hot"
            else {
                "pain_point": "pain",
                "target_user_and_scene": "scene",
                "why_test_now": "why",
                "continue_signal": "continue",
                "stop_signal": "stop",
            },
        }
        if lane == "hot":
            card["controversy_chart"] = {
                "support_ratio": 0.4,
                "oppose_ratio": 0.3,
                "neutral_ratio": 0.3,
                "support_point": "support",
                "oppose_point": "oppose",
                "neutral_point": "neutral",
                "debate_focus": "focus",
                "dominant_side": "support",
                "confidence": "medium",
            }
            card["controversy_meta"] = {
                "post_id": f"post-{card_id}",
                "sample_size": 8,
                "sampled_at": published_at,
                "fetch_status": "ok",
                "llm_summary_version": "test",
                "sample_quality": "medium",
                "summary_status": "ok",
            }
        return card

    published = [
        _build_card(
            card_id="card-main-1",
            lane="hot",
            source_event_at="2026-04-19T08:00:00Z",
            published_at="2026-04-19T09:00:00Z",
            source_link="https://reddit.com/main",
            title="主前台卡",
        ),
        _build_card(
            card_id="card-supplement-1",
            lane="signal",
            source_event_at="2026-04-12T09:00:00Z",
            published_at="2026-04-19T08:10:00Z",
            source_link="https://reddit.com/supplement",
            title="补充卡",
        ),
    ]
    published.extend(
        _build_card(
            card_id=f"card-stale-{index}",
            lane="signal",
            source_event_at="2026-03-01T09:00:00Z",
            published_at=f"2026-03-01T09:{index:02d}:00Z",
            source_link=f"https://reddit.com/stale-{index}",
            title=f"过期卡 {index}",
        )
        for index in range(1, 50)
    )
    payload = {
        "categories": [{"category_id": "all", "title": "全部", "description": "全部卡片"}],
        "published": published,
    }

    snapshot = build_mini_snapshot(payload)

    assert snapshot["card_count"] == len(published)
    assert snapshot["main_card_count"] == len(published)
    assert snapshot["supplement_card_count"] == 0
    assert snapshot["surface_contracts"]["supplement"]["max_event_age_days"] == 15
    assert all(item["surface_bucket"] == "main" for item in snapshot["cards"])


def test_build_mini_snapshot_exports_community_index() -> None:
    from app.services.hotpost.mini_snapshot import build_mini_snapshot

    def _card(card_id: str, *, community: str, lane: str, published_at: str) -> dict:
        card = {
            "card_id": card_id,
            "signal_id": f"sig-{card_id}",
            "card_type": "validate",
            "lane": lane,
            "category_id": "validate",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "source_domain_id": "ai-automation",
            "source_domain_name": "AI 与自动化",
            "source_event_at": published_at,
            "title": card_id,
            "summary_line": "summary",
            "audience": "工程师",
            "why_now": "why",
            "why_now_reason": "recurring_7d",
            "signal_level": "rising",
            "intent_tags": [],
            "top_community": community,
            "thread_count": 1,
            "community_count": 1,
            "source_module": {
                "primary_communities": [community],
                "top_community": community,
                "tone_tags": [],
                "thread_count": 1,
                "community_count": 1,
                "last_active_text": "近24小时",
            },
            "preview_quote": {
                "text": "quote",
                "community": community,
                "permalink": f"https://www.reddit.com/{community}/comments/{card_id}/q1",
            },
            "published_at": published_at,
            "quotes": [
                {
                    "text": "quote",
                    "community": community,
                    "permalink": f"https://www.reddit.com/{community}/comments/{card_id}/q1",
                }
            ],
            "source_link": f"https://www.reddit.com/{community}/comments/{card_id}",
            "detail": {
                "pain_point": "pain",
                "target_user_and_scene": "scene",
                "why_test_now": "why",
                "continue_signal": "continue",
                "stop_signal": "stop",
            },
        }
        if lane == "hot":
            card["controversy_chart"] = {
                "support_ratio": 0.4,
                "oppose_ratio": 0.3,
                "neutral_ratio": 0.3,
                "support_point": "support",
                "oppose_point": "oppose",
                "neutral_point": "neutral",
                "debate_focus": "focus",
                "dominant_side": "support",
                "confidence": "medium",
            }
            card["controversy_meta"] = {
                "post_id": f"post-{card_id}",
                "sample_size": 8,
                "sampled_at": published_at,
                "fetch_status": "ok",
                "llm_summary_version": "test",
                "sample_quality": "medium",
                "summary_status": "ok",
            }
        return card

    snapshot = build_mini_snapshot(
        {
            "categories": [{"category_id": "all", "title": "全部", "description": "全部卡片"}],
            "published": [
                _card("card-1", community="r/agi", lane="signal", published_at="2026-05-05T11:00:00Z"),
                _card("card-2", community="r/agi", lane="hot", published_at="2026-05-05T12:00:00Z"),
                _card("card-3", community="r/OpenAI", lane="hot", published_at="2026-05-05T13:00:00Z"),
            ],
        }
    )

    assert snapshot["communities"][:2] == [
        {
            "name": "r/agi",
            "card_count": 2,
            "top_card_count": 2,
            "lanes": ["hot", "signal"],
            "categories": ["AI 与自动化"],
            "latest_published_at": "2026-05-05T12:00:00Z",
        },
        {
            "name": "r/OpenAI",
            "card_count": 1,
            "top_card_count": 1,
            "lanes": ["hot"],
            "categories": ["AI 与自动化"],
            "latest_published_at": "2026-05-05T13:00:00Z",
        },
    ]


def test_build_mini_snapshot_keeps_same_day_block_before_old_breakdown() -> None:
    from app.services.hotpost.mini_snapshot import build_mini_snapshot

    def _card(card_id: str, *, lane: str, published_at: str, source_event_at: str | None = None) -> dict:
        source_event_at = source_event_at or published_at
        card = {
            "card_id": card_id,
            "signal_id": f"sig-{card_id}",
            "card_type": "write" if lane == "breakdown" else "validate",
            "lane": lane,
            "category_id": "validate",
            "source_scope_id": "ecommerce-sellers",
            "source_scope_name": "电商与卖家",
            "source_domain_id": "ecommerce-sellers",
            "source_domain_name": "电商与卖家",
            "source_event_at": source_event_at,
            "title": f"{lane} card {card_id}",
            "summary_line": "summary",
            "audience": "卖家",
            "why_now": "why now",
            "why_now_reason": "new_threads_24h",
            "signal_level": "hot" if lane == "hot" else "rising",
            "intent_tags": ["趋势变化"],
            "top_community": "r/ecommerce",
            "thread_count": 1,
            "community_count": 1,
            "source_module": {
                "primary_communities": ["r/ecommerce"],
                "top_community": "r/ecommerce",
                "tone_tags": [],
                "thread_count": 1,
                "community_count": 1,
                "last_active_text": "近24小时",
            },
            "preview_quote": {
                "text": "quote",
                "community": "r/ecommerce",
                "permalink": f"https://www.reddit.com/r/ecommerce/comments/{card_id}/q1",
            },
            "published_at": published_at,
            "quotes": [
                {
                    "text": "quote",
                    "community": "r/ecommerce",
                    "permalink": f"https://www.reddit.com/r/ecommerce/comments/{card_id}/q1",
                }
            ],
            "source_link": f"https://www.reddit.com/r/ecommerce/comments/{card_id}",
            "detail": {
                "pain_point": "pain",
                "target_user_and_scene": "scene",
                "why_test_now": "why",
                "continue_signal": "continue",
                "stop_signal": "stop",
            },
        }
        if lane == "hot":
            card["detail"] = {
                "flashpoint": "flash",
                "fight_line": "fight",
                "why_test_now": "why",
                "continue_signal": "continue",
                "stop_signal": "stop",
            }
            card["controversy_chart"] = {
                "support_ratio": 0.4,
                "oppose_ratio": 0.3,
                "neutral_ratio": 0.3,
                "support_point": "support",
                "oppose_point": "oppose",
                "neutral_point": "neutral",
                "debate_focus": "focus",
                "dominant_side": "support",
                "confidence": "medium",
            }
            card["controversy_meta"] = {
                "post_id": f"post-{card_id}",
                "sample_size": 8,
                "sampled_at": published_at,
                "fetch_status": "ok",
                "llm_summary_version": "test",
                "sample_quality": "medium",
                "summary_status": "ok",
            }
        if lane == "breakdown":
            card["detail"] = {
                "problem": "problem",
                "why_it_matters": "matters",
                "pattern": "pattern",
                "action": "action",
            }
        return card

    same_day_cards = [
        _card(
            f"same-day-{index}",
            lane="hot" if index % 3 == 0 else "signal",
            published_at=f"2026-05-01T04:{index:02d}:00Z",
        )
        for index in range(29)
    ]
    old_breakdown = _card(
        "old-breakdown",
        lane="breakdown",
        published_at="2026-04-30T09:00:00Z",
        source_event_at="2026-04-30T08:00:00Z",
    )
    payload = {
        "categories": [{"category_id": "all", "title": "全部", "description": "全部卡片"}],
        "published": [*same_day_cards, old_breakdown],
    }

    snapshot = build_mini_snapshot(payload)

    ordered_ids = [item["card_id"] for item in snapshot["cards"]]
    same_day_indices = [index for index, card_id in enumerate(ordered_ids) if str(card_id).startswith("same-day-")]

    assert same_day_indices == list(range(len(same_day_cards)))
    assert ordered_ids.index("old-breakdown") == len(same_day_cards)


def test_build_mini_snapshot_keeps_previous_day_cards_directly_after_today_cards() -> None:
    from app.services.hotpost.mini_snapshot import build_mini_snapshot

    def _card(card_id: str, *, lane: str, scope_id: str, published_at: str) -> dict:
        card = {
            "card_id": card_id,
            "signal_id": f"sig-{card_id}",
            "card_type": "validate",
            "lane": lane,
            "category_id": "validate",
            "source_scope_id": scope_id,
            "source_scope_name": "AI 与自动化" if scope_id == "ai-automation" else "电商与卖家",
            "source_domain_id": scope_id,
            "source_domain_name": "AI 与自动化" if scope_id == "ai-automation" else "电商与卖家",
            "source_event_at": published_at,
            "title": card_id,
            "summary_line": "summary",
            "audience": "读者",
            "why_now": "why now",
            "why_now_reason": "new_threads_24h",
            "signal_level": "hot" if lane == "hot" else "rising",
            "intent_tags": ["趋势变化"],
            "top_community": "r/OpenAI",
            "thread_count": 1,
            "community_count": 1,
            "source_module": {
                "primary_communities": ["r/OpenAI"],
                "top_community": "r/OpenAI",
                "tone_tags": [],
                "thread_count": 1,
                "community_count": 1,
                "last_active_text": "近24小时",
            },
            "preview_quote": {
                "text": "quote",
                "community": "r/OpenAI",
                "permalink": f"https://www.reddit.com/r/OpenAI/comments/{card_id}/q1",
            },
            "published_at": published_at,
            "quotes": [
                {
                    "text": "quote",
                    "community": "r/OpenAI",
                    "permalink": f"https://www.reddit.com/r/OpenAI/comments/{card_id}/q1",
                }
            ],
            "source_link": f"https://www.reddit.com/r/OpenAI/comments/{card_id}",
            "detail": {
                "pain_point": "pain",
                "target_user_and_scene": "scene",
                "why_test_now": "why",
                "continue_signal": "continue",
                "stop_signal": "stop",
            },
        }
        if lane == "hot":
            card["detail"] = {
                "flashpoint": "flash",
                "fight_line": "fight",
                "why_test_now": "why",
                "continue_signal": "continue",
                "stop_signal": "stop",
            }
            card["controversy_chart"] = {
                "support_ratio": 0.4,
                "oppose_ratio": 0.3,
                "neutral_ratio": 0.3,
                "support_point": "support",
                "oppose_point": "oppose",
                "neutral_point": "neutral",
                "debate_focus": "focus",
                "dominant_side": "support",
                "confidence": "medium",
            }
            card["controversy_meta"] = {
                "post_id": f"post-{card_id}",
                "sample_size": 8,
                "sampled_at": published_at,
                "fetch_status": "ok",
                "llm_summary_version": "test",
                "sample_quality": "medium",
                "summary_status": "ok",
            }
        return card

    today_cards = [
        _card(
            f"today-{index}",
            lane="hot" if index % 3 == 0 else "signal",
            scope_id="ai-automation" if index % 2 == 0 else "ecommerce-sellers",
            published_at=f"2026-05-06T04:{index:02d}:00Z",
        )
        for index in range(11)
    ]
    yesterday_cards = [
        _card(
            f"yesterday-{index}",
            lane="hot" if index % 2 == 0 else "signal",
            scope_id="ai-automation",
            published_at=f"2026-05-05T11:{index:02d}:00Z",
        )
        for index in range(25)
    ]
    older_cards = [
        _card(
            f"older-{index}",
            lane="hot" if index % 2 == 0 else "signal",
            scope_id="ecommerce-sellers",
            published_at=f"2026-05-04T11:{index:02d}:00Z",
        )
        for index in range(10)
    ]
    snapshot = build_mini_snapshot(
        {
            "categories": [{"category_id": "all", "title": "全部", "description": "全部卡片"}],
            "published": [*today_cards, *yesterday_cards, *older_cards],
        }
    )

    ordered_ids = [item["card_id"] for item in snapshot["cards"]]
    first_older_index = min(index for index, card_id in enumerate(ordered_ids) if card_id.startswith("older-"))
    last_yesterday_index = max(index for index, card_id in enumerate(ordered_ids) if card_id.startswith("yesterday-"))

    assert first_older_index > last_yesterday_index
    assert all(card_id.startswith(("today-", "yesterday-")) for card_id in ordered_ids[:30])


def test_build_mini_snapshot_uses_operational_publish_order_without_old_card_mix() -> None:
    from app.services.hotpost.mini_snapshot import build_mini_snapshot

    def _card(card_id: str, *, lane: str, published_at: str) -> dict:
        card = {
            "card_id": card_id,
            "signal_id": f"sig-{card_id}",
            "card_type": "write" if lane == "breakdown" else "validate",
            "lane": lane,
            "category_id": "validate",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "source_domain_id": "ai-automation",
            "source_domain_name": "AI 与自动化",
            "source_event_at": published_at,
            "title": card_id,
            "summary_line": "summary",
            "audience": "读者",
            "why_now": "why now",
            "why_now_reason": "new_threads_24h",
            "signal_level": "hot" if lane == "hot" else "rising",
            "intent_tags": ["趋势变化"],
            "top_community": "r/OpenAI",
            "thread_count": 1,
            "community_count": 1,
            "source_module": {
                "primary_communities": ["r/OpenAI"],
                "top_community": "r/OpenAI",
                "tone_tags": [],
                "thread_count": 1,
                "community_count": 1,
                "last_active_text": "近24小时",
            },
            "preview_quote": {
                "text": "quote",
                "community": "r/OpenAI",
                "permalink": f"https://www.reddit.com/r/OpenAI/comments/{card_id}/q1",
            },
            "published_at": published_at,
            "quotes": [
                {
                    "text": "quote",
                    "community": "r/OpenAI",
                    "permalink": f"https://www.reddit.com/r/OpenAI/comments/{card_id}/q1",
                }
            ],
            "source_link": f"https://www.reddit.com/r/OpenAI/comments/{card_id}",
            "detail": {
                "pain_point": "pain",
                "target_user_and_scene": "scene",
                "why_test_now": "why",
                "continue_signal": "continue",
                "stop_signal": "stop",
            },
        }
        if lane == "hot":
            card["detail"] = {
                "flashpoint": "flash",
                "fight_line": "fight",
                "why_test_now": "why",
                "continue_signal": "continue",
                "stop_signal": "stop",
            }
            card["controversy_chart"] = {
                "support_ratio": 0.4,
                "oppose_ratio": 0.3,
                "neutral_ratio": 0.3,
                "support_point": "support",
                "oppose_point": "oppose",
                "neutral_point": "neutral",
                "debate_focus": "focus",
                "dominant_side": "support",
                "confidence": "medium",
            }
            card["controversy_meta"] = {
                "post_id": f"post-{card_id}",
                "sample_size": 8,
                "sampled_at": published_at,
                "fetch_status": "ok",
                "llm_summary_version": "test",
                "sample_quality": "medium",
                "summary_status": "ok",
            }
        if lane == "breakdown":
            card["detail"] = {
                "problem": "problem",
                "why_it_matters": "matters",
                "pattern": "pattern",
                "action": "action",
            }
        return card

    cards = [
        _card("new-signal", lane="signal", published_at="2026-05-06T04:00:00Z"),
        _card("old-breakdown", lane="breakdown", published_at="2026-04-30T04:00:00Z"),
        _card("yesterday-hot", lane="hot", published_at="2026-05-05T04:00:00Z"),
        _card("old-hot", lane="hot", published_at="2026-05-01T04:00:00Z"),
    ]
    snapshot = build_mini_snapshot(
        {
            "categories": [{"category_id": "all", "title": "全部", "description": "全部卡片"}],
            "published": cards,
        }
    )

    assert [item["card_id"] for item in snapshot["cards"]] == [
        "new-signal",
        "yesterday-hot",
        "old-hot",
        "old-breakdown",
    ]
