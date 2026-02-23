from __future__ import annotations

from app.services.analysis_engine import _looks_like_reddit_post_id


def test_looks_like_reddit_post_id_accepts_common_shapes() -> None:
    assert _looks_like_reddit_post_id("1abcde") is True
    assert _looks_like_reddit_post_id("t3_1abcde") is True
    assert _looks_like_reddit_post_id("123456") is True


def test_looks_like_reddit_post_id_rejects_demo_ids_and_invalid_shapes() -> None:
    assert _looks_like_reddit_post_id("") is False
    assert _looks_like_reddit_post_id("abc") is False
    assert _looks_like_reddit_post_id("r/FacebookAds-opportunity-wish") is False
    assert _looks_like_reddit_post_id("r/shopify") is False

