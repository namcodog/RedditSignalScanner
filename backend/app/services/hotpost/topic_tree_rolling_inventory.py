from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from typing import Any
import json

from app.services.hotpost.intake_freshness_gate import LANE_WINDOWS_HOURS
from app.services.hotpost.topic_tree_governance_audit import source_health_signal_for_record
from app.services.hotpost.topic_tree_governance_common import build_topic_tree_record, parse_dt
from app.services.hotpost.topic_tree_publish_surface_planner import TopicTreePublishSurfacePlanner

RELEASES_DIR = Path(__file__).resolve().parents[3] / "data" / "hotpost" / "mini_snapshots" / "releases"
RECENT_RELEASE_HISTORY_LIMIT = 4


def build_governed_rolling_inventory(
    cards: list[dict[str, Any]],
    *,
    max_cards: int = 250,
    reference_time: datetime | None = None,
    previous_cards: list[dict[str, Any]] | None = None,
    stable_front_window: int = 30,
) -> list[dict[str, Any]]:
    if max_cards <= 0 or not cards:
        return []

    resolved_reference = reference_time or datetime.now(timezone.utc)
    ordered = sorted(cards, key=_recency_sort_key, reverse=True)
    eligible = [
        dict(item)
        for item in ordered
        if _is_inventory_eligible(item, reference_time=resolved_reference)
    ]
    if not eligible:
        return []

    target_total = min(max_cards, len(eligible))
    planner = TopicTreePublishSurfacePlanner(
        history_items=ordered,
        candidate_items=eligible,
        reference_time=resolved_reference,
    )
    present_lanes = {
        str(item.get("lane") or "").strip()
        for item in eligible
        if str(item.get("lane") or "").strip()
    }
    lane_targets = {lane: 1 for lane in present_lanes}
    lane_counts: Counter[str] = Counter()
    caps = rolling_inventory_caps(target_total)
    previous_positions = {
        str(item.get("card_id") or ""): index
        for index, item in enumerate(previous_cards or [])
        if str(item.get("card_id") or "")
    }
    recent_histories = _load_recent_release_histories(limit=RECENT_RELEASE_HISTORY_LIMIT) if previous_cards is not None else []
    recent_tail_penalties = _recent_tail_penalties(
        recent_histories,
        stable_front_window=stable_front_window,
    )
    recent_tail_counts = _recent_tail_counts(
        recent_histories,
        stable_front_window=stable_front_window,
    )

    selected: list[dict[str, Any]] = []
    used_indexes: set[int] = set()

    while len(selected) < target_total:
        best_index: int | None = None
        best_key: tuple[Any, ...] | None = None
        override_index: int | None = None
        override_key: tuple[Any, ...] | None = None

        for index, item in enumerate(eligible):
            if index in used_indexes:
                continue
            record = build_topic_tree_record(
                item,
                reference_time=resolved_reference,
                treat_as_published=True,
            )
            source_health = source_health_signal_for_record(
                record=record,
                history_records=planner.history_records,
                selected_records=planner.selected_records,
                reference_time=resolved_reference,
            )
            selection_key = _inventory_selection_key(
                item=item,
                planner=planner,
                lane_counts=lane_counts,
                lane_targets=lane_targets,
                reference_time=resolved_reference,
                source_health=source_health,
                previous_positions=previous_positions,
                recent_tail_penalties=recent_tail_penalties,
                recent_tail_counts=recent_tail_counts,
                stable_front_window=stable_front_window,
            )
            if _fits_inventory_caps(
                record=record,
                selected=selected,
                caps=caps,
            ):
                if best_key is None or selection_key < best_key:
                    best_key = selection_key
                    best_index = index
                continue
            if not _allow_inventory_override(
                record=record,
                planner=planner,
                source_health=source_health,
            ):
                continue
            if override_key is None or selection_key < override_key:
                override_key = selection_key
                override_index = index

        chosen_index = best_index if best_index is not None else override_index
        if chosen_index is None:
            break

        chosen = eligible[chosen_index]
        selected.append(chosen)
        used_indexes.add(chosen_index)
        planner.record_selection(chosen)
        lane = str(chosen.get("lane") or "").strip()
        if lane:
            lane_counts[lane] += 1

    repaired = _repair_inventory_caps(
        selected,
        caps=caps,
        recent_tail_penalties=recent_tail_penalties,
        reference_time=resolved_reference,
    )
    return sorted(repaired, key=_recency_sort_key, reverse=True)


def rolling_inventory_caps(target_total: int) -> dict[str, int]:
    return {
        "scope": max(2, ceil(target_total * 0.5)),
        "pack": 14,
        "community": 5,
    }


def _repair_inventory_caps(
    selected: list[dict[str, Any]],
    *,
    caps: dict[str, int],
    recent_tail_penalties: dict[str, int],
    reference_time: datetime,
) -> list[dict[str, Any]]:
    working = [dict(item) for item in selected]
    while True:
        records = [
            build_topic_tree_record(
                item,
                reference_time=reference_time,
                treat_as_published=True,
            )
            for item in working
        ]
        scope_counts = Counter(record.source_scope_id for record in records if record.source_scope_id)
        pack_counts = Counter(record.topic_pack_id for record in records if record.topic_pack_id)
        community_counts = Counter(record.community for record in records if record.community)
        over_communities = {
            name: count - caps["community"]
            for name, count in community_counts.items()
            if count > caps["community"]
        }
        over_packs = {
            name: count - caps["pack"]
            for name, count in pack_counts.items()
            if count > caps["pack"]
        }
        if not over_communities and not over_packs:
            return working
        remove_index = _pick_inventory_removal_index(
            items=working,
            records=records,
            scope_counts=scope_counts,
            over_communities=over_communities,
            over_packs=over_packs,
            recent_tail_penalties=recent_tail_penalties,
            reference_time=reference_time,
        )
        if remove_index is None:
            return working
        del working[remove_index]


def _pick_inventory_removal_index(
    *,
    items: list[dict[str, Any]],
    records: list[Any],
    scope_counts: Counter[str],
    over_communities: dict[str, int],
    over_packs: dict[str, int],
    recent_tail_penalties: dict[str, int],
    reference_time: datetime,
) -> int | None:
    best_index: int | None = None
    best_key: tuple[Any, ...] | None = None
    for index, (item, record) in enumerate(zip(items, records)):
        community_excess = int(over_communities.get(record.community or "", 0))
        pack_excess = int(over_packs.get(record.topic_pack_id or "", 0))
        if community_excess <= 0 and pack_excess <= 0:
            continue
        scope_id = str(record.source_scope_id or "")
        preserve_scope_penalty = 1 if scope_id and scope_counts.get(scope_id, 0) <= 1 else 0
        age_ratio = _age_ratio(record=record, reference_time=reference_time)
        recent_tail_penalty = int(recent_tail_penalties.get(str(item.get("card_id") or ""), 0))
        removal_key = (
            preserve_scope_penalty,
            -(community_excess + pack_excess),
            -recent_tail_penalty,
            1 if record.is_new_source else 0,
            -round(age_ratio, 4),
            _recency_sort_key(item),
        )
        if best_key is None or removal_key < best_key:
            best_key = removal_key
            best_index = index
    return best_index


def _fits_inventory_caps(
    *,
    record: Any,
    selected: list[dict[str, Any]],
    caps: dict[str, int],
) -> bool:
    selected_records = [
        build_topic_tree_record(
            item,
            reference_time=record.published_at or record.source_event_at or datetime.now(timezone.utc),
            treat_as_published=True,
        )
        for item in selected
    ]
    scope_counts = Counter(current.source_scope_id for current in selected_records if current.source_scope_id)
    pack_counts = Counter(current.topic_pack_id for current in selected_records if current.topic_pack_id)
    community_counts = Counter(current.community for current in selected_records if current.community)

    if record.source_scope_id and scope_counts.get(record.source_scope_id, 0) + 1 > caps["scope"]:
        return False
    if record.topic_pack_id and pack_counts.get(record.topic_pack_id, 0) + 1 > caps["pack"]:
        return False
    if record.community and community_counts.get(record.community, 0) + 1 > caps["community"]:
        return False
    return True


def _allow_inventory_override(
    *,
    record: Any,
    planner: TopicTreePublishSurfacePlanner,
    source_health: dict[str, Any],
) -> bool:
    selected_scope_ids = {
        current.source_scope_id
        for current in planner.selected_records
        if current.source_scope_id
    }
    if record.source_scope_id and len(selected_scope_ids) < min(len(planner.available_scope_ids), 3):
        return record.source_scope_id not in selected_scope_ids
    if bool(source_health.get("relieves_old_source_concentration")):
        return True
    return bool(record.is_new_source)


def _inventory_selection_key(
    *,
    item: dict[str, Any],
    planner: TopicTreePublishSurfacePlanner,
    lane_counts: Counter[str],
    lane_targets: dict[str, int],
    reference_time: datetime,
    source_health: dict[str, Any],
    previous_positions: dict[str, int],
    recent_tail_penalties: dict[str, int],
    recent_tail_counts: dict[str, int],
    stable_front_window: int,
) -> tuple[Any, ...]:
    record = build_topic_tree_record(
        item,
        reference_time=reference_time,
        treat_as_published=True,
    )
    age_ratio = _age_ratio(record=record, reference_time=reference_time)
    target_fresh_penalty = int(age_ratio > 1.0)
    card_id = str(item.get("card_id") or "")
    previous_position = previous_positions.get(card_id)
    previous_tail_repeat_penalty = int(previous_position is not None and previous_position >= stable_front_window)
    recent_tail_penalty = int(recent_tail_penalties.get(card_id, 0))
    recent_tail_count = int(recent_tail_counts.get(card_id, 0))
    return (
        target_fresh_penalty,
        0 if source_health.get("relieves_old_source_concentration") else 1,
        recent_tail_penalty,
        recent_tail_count,
        round(age_ratio, 4),
        previous_tail_repeat_penalty,
        planner.sort_key(
            item,
            lane_counts=lane_counts,
            lane_targets=lane_targets,
        ),
        _recency_sort_key(item),
    )


def _age_ratio(*, record: Any, reference_time: datetime) -> float:
    event_at = record.source_event_at or record.published_at
    if event_at is None:
        return 99.0
    lane = str(record.lane or "").strip()
    target_hours = float(LANE_WINDOWS_HOURS.get(lane, {}).get("target", 24.0))
    age_hours = max((reference_time - event_at).total_seconds() / 3600.0, 0.0)
    if target_hours <= 0:
        return 0.0
    return age_hours / target_hours


def _is_inventory_eligible(item: dict[str, Any], *, reference_time: datetime) -> bool:
    lane = str(item.get("lane") or "").strip()
    if not lane or lane not in LANE_WINDOWS_HOURS:
        return False
    event_at = parse_dt(item.get("source_event_at")) or parse_dt(item.get("published_at"))
    if event_at is None:
        return False
    max_hours = float(LANE_WINDOWS_HOURS[lane]["max"])
    age_hours = max((reference_time - event_at).total_seconds() / 3600.0, 0.0)
    return age_hours <= max_hours


def _recency_sort_key(item: dict[str, Any]) -> tuple[str, str]:
    published_at = str(item.get("published_at") or "")
    source_event_at = str(item.get("source_event_at") or "")
    card_id = str(item.get("card_id") or "")
    return (published_at or source_event_at, card_id)


def _load_recent_release_histories(*, limit: int) -> list[list[dict[str, Any]]]:
    if limit <= 0 or not RELEASES_DIR.exists():
        return []
    histories: list[list[dict[str, Any]]] = []
    release_paths = sorted(
        RELEASES_DIR.glob("release-*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in release_paths[:limit]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        cards = payload.get("cards") or []
        if not isinstance(cards, list):
            continue
        histories.append([dict(item) for item in cards if isinstance(item, dict)])
    return histories


def _recent_tail_penalties(
    histories: list[list[dict[str, Any]]],
    *,
    stable_front_window: int,
) -> dict[str, int]:
    penalties: dict[str, int] = {}
    history_count = len(histories)
    for history_index, cards in enumerate(histories):
        weight = max(history_count - history_index, 1)
        for position, item in enumerate(cards):
            if position < stable_front_window:
                continue
            card_id = str(item.get("card_id") or "")
            if not card_id:
                continue
            penalties[card_id] = penalties.get(card_id, 0) + weight
    return penalties


def _recent_tail_counts(
    histories: list[list[dict[str, Any]]],
    *,
    stable_front_window: int,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for cards in histories:
        seen: set[str] = set()
        for position, item in enumerate(cards):
            if position < stable_front_window:
                continue
            card_id = str(item.get("card_id") or "")
            if not card_id or card_id in seen:
                continue
            counts[card_id] = counts.get(card_id, 0) + 1
            seen.add(card_id)
    return counts


__all__ = ["build_governed_rolling_inventory", "rolling_inventory_caps"]
