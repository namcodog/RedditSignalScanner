from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from math import ceil
from typing import Any

from app.services.hotpost.topic_tree_governance_audit import (
    rotation_signal_for_record,
    source_health_signal_for_record,
)
from app.services.hotpost.topic_tree_governance_common import (
    TopicTreeRecord,
    build_topic_tree_record,
    build_topic_tree_records,
)


class TopicTreePublishSurfacePlanner:
    def __init__(
        self,
        *,
        history_items: list[dict[str, Any]],
        candidate_items: list[dict[str, Any]],
        reference_time: datetime | None = None,
    ) -> None:
        self.reference_time = reference_time or datetime.now(timezone.utc)
        self.history_records = build_topic_tree_records(
            history_items,
            reference_time=self.reference_time,
            treat_as_published=False,
        )
        self.available_records = build_topic_tree_records(
            candidate_items,
            reference_time=self.reference_time,
            treat_as_published=True,
        )
        self.available_scope_ids = sorted(
            {record.source_scope_id for record in self.available_records if record.source_scope_id}
        )
        self.selected_records: list[TopicTreeRecord] = []

    def sort_key(
        self,
        item: dict[str, Any],
        *,
        lane_counts: Counter[str],
        lane_targets: dict[str, int],
    ) -> tuple[Any, ...]:
        record = build_topic_tree_record(
            item,
            reference_time=self.reference_time,
            treat_as_published=True,
        )
        selected_scope_counts = Counter(
            current.source_scope_id for current in self.selected_records if current.source_scope_id
        )
        selected_pack_counts = Counter(
            current.topic_pack_id for current in self.selected_records if current.topic_pack_id
        )
        selected_community_counts = Counter(
            current.community for current in self.selected_records if current.community
        )
        history_scope_counts = Counter(
            current.source_scope_id for current in self.history_records if current.source_scope_id
        )
        history_pack_counts = Counter(
            current.topic_pack_id for current in self.history_records if current.topic_pack_id
        )
        history_community_counts = Counter(
            current.community for current in self.history_records if current.community
        )

        current_size = len(self.selected_records) + 1
        scope_soft_limit = max(1, ceil(current_size * 0.4))
        pack_soft_limit = max(2, ceil(current_size / 3))
        community_soft_limit = 2 if current_size >= 10 else 1 if current_size >= 4 else current_size

        selected_scope_ids = {
            current.source_scope_id for current in self.selected_records if current.source_scope_id
        }
        scope_missing_priority = 1
        if record.source_scope_id and len(selected_scope_ids) < min(len(self.available_scope_ids), 3):
            scope_missing_priority = 0 if record.source_scope_id not in selected_scope_ids else 1

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

        selected_scope_penalty = max(
            selected_scope_counts.get(record.source_scope_id, 0) - scope_soft_limit + 1,
            0,
        )
        selected_pack_penalty = (
            max(selected_pack_counts.get(record.topic_pack_id, 0) - pack_soft_limit + 1, 0)
            if record.topic_pack_id
            else 0
        )
        selected_community_penalty = (
            max(selected_community_counts.get(record.community, 0) - community_soft_limit + 1, 0)
            if record.community
            else 0
        )

        top_history_community = history_community_counts.most_common(1)[0][0] if history_community_counts else None
        top_history_pack = history_pack_counts.most_common(1)[0][0] if history_pack_counts else None
        dominant_history_community_penalty = int(
            bool(
                record.community
                and top_history_community
                and record.community == top_history_community
                and history_community_counts.get(top_history_community, 0) >= 3
            )
        )
        dominant_history_pack_penalty = int(
            bool(
                record.topic_pack_id
                and top_history_pack
                and record.topic_pack_id == top_history_pack
                and history_pack_counts.get(top_history_pack, 0) >= 4
            )
        )
        dominant_history_scope_penalty = int(
            bool(
                record.source_scope_id
                and history_scope_counts
                and record.source_scope_id == history_scope_counts.most_common(1)[0][0]
                and history_scope_counts.most_common(1)[0][1] >= 6
            )
        )

        return (
            1 if rotation["cooldown_penalty"] else 0,
            scope_missing_priority,
            0 if source_health["relieves_old_source_concentration"] else 1,
            1 if source_health["dominant_old_source_penalty"] else 0,
            int(source_health["selected_community_penalty"]),
            selected_community_penalty,
            selected_pack_penalty,
            selected_scope_penalty,
            dominant_history_community_penalty,
            dominant_history_pack_penalty,
            dominant_history_scope_penalty,
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


__all__ = ["TopicTreePublishSurfacePlanner"]
