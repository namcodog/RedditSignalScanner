from __future__ import annotations

from collections.abc import Iterable


RECALL_PRIORITY_CLUSTER_IDS = (
    "key-people-and-route",
    "ai-product-and-adoption",
    "platform-policy-shifts",
)

PUBLISH_PRIORITY_CLUSTER_IDS = (
    *RECALL_PRIORITY_CLUSTER_IDS,
    "small-goods",
)


def has_recall_priority_cluster(
    topic_cluster_id: str | None = None,
    topic_cluster_ids: Iterable[str] | None = None,
) -> bool:
    cluster_ids = _normalize_cluster_ids(topic_cluster_id, topic_cluster_ids)
    return bool(cluster_ids & set(RECALL_PRIORITY_CLUSTER_IDS))


def _normalize_cluster_ids(
    topic_cluster_id: str | None = None,
    topic_cluster_ids: Iterable[str] | None = None,
) -> set[str]:
    cluster_ids = {
        str(item).strip()
        for item in (topic_cluster_ids or ())
        if str(item).strip()
    }
    if str(topic_cluster_id or "").strip():
        cluster_ids.add(str(topic_cluster_id).strip())
    return cluster_ids


__all__ = [
    "PUBLISH_PRIORITY_CLUSTER_IDS",
    "RECALL_PRIORITY_CLUSTER_IDS",
    "has_recall_priority_cluster",
]
