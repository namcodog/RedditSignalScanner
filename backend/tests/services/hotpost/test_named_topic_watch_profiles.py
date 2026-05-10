from __future__ import annotations


def test_crossborder_sku_selection_profile_uses_three_layer_truth_sources() -> None:
    from app.services.hotpost.named_topic_watch_profiles import load_named_topic_watch_profile

    watches = load_named_topic_watch_profile("crossborder-sku-selection-7d")
    by_topic = {watch.topic_id: watch for watch in watches}

    assert set(by_topic) == {
        "crossborder-sku-7d-user-demand",
        "crossborder-sku-7d-seller-validation",
        "crossborder-sku-7d-crowdfunding-validation",
    }
    assert by_topic["crossborder-sku-7d-user-demand"].topic_pack_id == "selection-signals"
    assert by_topic["crossborder-sku-7d-seller-validation"].topic_pack_id == "category-winds"
    assert by_topic["crossborder-sku-7d-crowdfunding-validation"].topic_pack_id == "selection-signals"
    assert "giftideas" not in {item.lower() for item in by_topic["crossborder-sku-7d-user-demand"].subreddits}
    assert "AmazonSeller" in by_topic["crossborder-sku-7d-seller-validation"].subreddits
    assert "kickstarter" in by_topic["crossborder-sku-7d-crowdfunding-validation"].subreddits


def test_small_goods_broad_no_longer_defaults_to_giftideas() -> None:
    from app.services.hotpost.named_topic_watch_profiles import load_named_topic_watch_profile

    watches = load_named_topic_watch_profile("selection-30d-small-goods-broad")
    subreddits = {subreddit.lower() for watch in watches for subreddit in watch.subreddits}
    topic_ids = {watch.topic_id for watch in watches}

    assert "giftideas" not in subreddits
    assert "small-goods-30d-broad-gift" not in topic_ids
