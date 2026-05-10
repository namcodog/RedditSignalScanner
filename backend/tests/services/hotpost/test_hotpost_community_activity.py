from __future__ import annotations

from app.services.hotpost.hotpost_community_activity import build_community_activity


def test_build_community_activity_tracks_card_topic_clusters() -> None:
    activity = build_community_activity(
        [
            {
                "card_id": "card-1",
                "title": "FBA fee pressure",
                "preview_quote": {"community": "r/FulfillmentByAmazon"},
                "topic_pack_id": "kill-signals",
                "topic_cluster_id": "unit-economics-and-platform-risk",
                "topic_cluster_ids": ["unit-economics-and-platform-risk"],
            }
        ]
    )

    item = activity["fulfillmentbyamazon"]

    assert item.topic_packs["kill-signals"] == 1
    assert item.topic_clusters["unit-economics-and-platform-risk"] == 1
