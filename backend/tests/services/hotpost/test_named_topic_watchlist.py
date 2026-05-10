from __future__ import annotations


def test_daily_watchlist_covers_priority_topics() -> None:
    from app.services.hotpost.named_topic_watchlist import get_default_named_topic_preset, resolve_named_topic_watchlist

    assert get_default_named_topic_preset() == "daily-watchlist"
    items = resolve_named_topic_watchlist(preset="daily-watchlist")
    topic_ids = {item.topic_id for item in items}
    scope_ids = {item.scope_id for item in items}

    assert "karpathy-llm-wiki" in topic_ids
    assert "claude-mythos" in topic_ids
    assert "ai-route-shifts" in topic_ids
    assert "platform-policy-watch" in topic_ids
    assert "prompt-engineering" in topic_ids
    assert "ai-product-adoption" in topic_ids
    assert "checkout-conversion" in topic_ids
    assert "form-friction-conversion" in topic_ids
    assert "small-goods-watch" in topic_ids
    assert "flashlight-selection" in topic_ids
    assert "pet-supplies" in topic_ids
    assert scope_ids == {"ai-automation", "business-growth-ops", "ecommerce-sellers"}


def test_supply_repair_watchlist_targets_missing_packs() -> None:
    from app.services.hotpost.named_topic_watchlist import load_named_topic_registry, resolve_named_topic_watchlist

    items = resolve_named_topic_watchlist(preset="supply-repair-v1")
    topic_ids = {item.topic_id for item in items}

    assert topic_ids == {
        "mcp-workflows",
        "ai-route-shifts",
        "platform-policy-watch",
        "ai-product-adoption",
        "checkout-conversion",
        "form-friction-conversion",
        "category-demand-shift",
        "small-goods-watch",
    }

    registry = load_named_topic_registry()
    assert "mcp-workflows" in registry
    assert "pet-supplies" in registry
