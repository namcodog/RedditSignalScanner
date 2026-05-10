from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.services.hotpost.topic_tree_governance_audit import (
    build_topic_tree_governance_audit,
    build_tree_coverage_allocation_audit,
    rotation_signal_for_record,
    source_health_signal_for_record,
)
from app.services.hotpost.topic_tree_governance_common import (
    TopicTreeRecord,
    build_topic_tree_record,
    build_topic_tree_records,
)


class TopicTreeGovernancePlanner:
    def __init__(
        self,
        *,
        scope_id: str,
        history_items: list[dict[str, Any]],
        candidate_items: list[dict[str, Any]],
        reference_time: datetime | None = None,
    ) -> None:
        self.scope_id = scope_id
        self.reference_time = reference_time or datetime.now(timezone.utc)
        self.history_records = build_topic_tree_records(
            [item for item in history_items if str(item.get("source_scope_id") or "") == scope_id],
            reference_time=self.reference_time,
            treat_as_published=False,
        )
        self.available_records = build_topic_tree_records(
            [item for item in candidate_items if str(item.get("source_scope_id") or "") == scope_id],
            reference_time=self.reference_time,
            treat_as_published=True,
        )
        self.selected_records: list[TopicTreeRecord] = []

    def sort_key(
        self,
        item: dict[str, Any],
        *,
        lane_counts: Counter[str],
        lane_targets: dict[str, int],
    ) -> tuple[Any, ...]:
        record = build_topic_tree_record(item, reference_time=self.reference_time, treat_as_published=True)
        allocation = self._allocation_signal(record)
        rotation = rotation_signal_for_record(
            record=record,
            history_records=self.history_records,
            selected_records=self.selected_records,
            reference_time=self.reference_time,
        )
        source_health = source_health_signal_for_record(
            record=record,
            history_records=self.history_records,
            selected_records=self.selected_records,
            reference_time=self.reference_time,
        )
        lane_gap = int(lane_targets.get(record.lane, 0)) - int(lane_counts.get(record.lane, 0))
        return (
            1 if rotation["cooldown_penalty"] else 0,
            0 if allocation["pack_missing_3d"] else 1,
            0 if allocation["cluster_missing_3d"] else 1,
            0 if source_health["relieves_old_source_concentration"] else 1,
            1 if source_health["dominant_old_source_penalty"] else 0,
            int(source_health["selected_community_penalty"]),
            0 if record.is_new_source else 1,
            0 if lane_gap > 0 else 1,
            -max(lane_gap, 0),
            -record.score_hint,
            record.title,
        )

    def record_selection(self, item: dict[str, Any]) -> None:
        self.selected_records.append(
            build_topic_tree_record(
                item,
                reference_time=self.reference_time,
                treat_as_published=True,
            )
        )

    def build_audit(self, *, plan_items: list[dict[str, Any]], candidate_items: list[dict[str, Any]]) -> dict[str, Any]:
        planned_records = build_topic_tree_records(
            [item for item in plan_items if str(item.get("source_scope_id") or "") == self.scope_id],
            reference_time=self.reference_time,
            treat_as_published=True,
        )
        candidate_records = build_topic_tree_records(
            [item for item in candidate_items if str(item.get("source_scope_id") or "") == self.scope_id],
            reference_time=self.reference_time,
            treat_as_published=True,
        )
        return build_topic_tree_governance_audit(
            scope_id=self.scope_id,
            history_records=self.history_records,
            planned_records=planned_records,
            candidate_records=candidate_records,
            reference_time=self.reference_time,
        )

    def _allocation_signal(self, record: TopicTreeRecord) -> dict[str, Any]:
        allocation = build_tree_coverage_allocation_audit(
            scope_id=self.scope_id,
            history_records=self.history_records,
            planned_records=[*self.selected_records, record],
            candidate_records=self.available_records,
            reference_time=self.reference_time,
        )
        visible_pack_counts = allocation.get("visible_pack_counts") or {}
        visible_cluster_counts = allocation.get("visible_cluster_counts") or {}
        return {
            "pack_missing_3d": bool(record.topic_pack_id and visible_pack_counts.get(record.topic_pack_id, 0) == 1),
            "cluster_missing_3d": bool(record.topic_cluster_id and visible_cluster_counts.get(record.topic_cluster_id, 0) == 1),
        }


__all__ = ["TopicTreeGovernancePlanner"]
