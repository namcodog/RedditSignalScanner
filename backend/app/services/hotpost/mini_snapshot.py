from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any

from app.services.hotpost.card_payload_store import load_categories, load_published_cards, merge_published_cards
from app.services.hotpost.card_lane_policy import resolve_lane
from app.services.hotpost.card_content_rules_config import load_card_content_rules
from app.services.hotpost.hot_controversy_chart import enrich_hot_controversy_chart, refresh_hot_controversy_cards_sync
from app.services.hotpost.hotpost_supply_contract import get_supply_operation_defaults, get_supply_rolling_publish_mix
from app.services.hotpost.mini_snapshot_supplement import MAIN_SURFACE_BUCKET, build_mini_surface_contracts
from app.services.hotpost.semantic_readout import clean_readout_text_for_client
from app.services.hotpost.topic_tree_governance_common import parse_dt
from app.services.hotpost.topic_tree_visible_governance import select_governed_window_indices
from app.schemas.hotpost_validate_details import validation_detail_field_names_for_payload


def build_mini_snapshot(
    payload:Optional[ dict[str, Any]] = None,
    *,
    reference_time: datetime | None = None,
    previous_cards: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    source = payload or {}
    categories_source = (source.get("categories") or []) if payload is not None else load_categories()
    categories = [dict(item) for item in categories_source]
    published_cards = [
        _sanitize_card_for_snapshot(item)
        for item in ((source.get("published") or []) if payload is not None else load_published_cards())
    ]
    resolved_reference = reference_time
    if resolved_reference is None:
        if payload is None:
            resolved_reference = datetime.now(timezone.utc)
        else:
            reference_candidates = [
                parse_dt(item.get("published_at")) or parse_dt(item.get("source_event_at"))
                for item in published_cards
            ]
            resolved_reference = max(
                (value for value in reference_candidates if value is not None),
                default=datetime.now(timezone.utc),
            )
    # Product contract: the mini app must expose every published card.
    # We only reorder the front window; we no longer trim older published cards
    # out of the snapshot.
    main_cards = sorted(published_cards, key=lambda item: item["published_at"], reverse=True)
    main_cards = _promote_same_day_published_cards(
        selected_cards=main_cards,
        published_cards=published_cards,
        reference_time=resolved_reference,
    )
    _require_hot_controversy_ready(main_cards)
    main_cards = _apply_homepage_shelf_mix(main_cards, reference_time=resolved_reference)
    main_cards = [{**item, "surface_bucket": MAIN_SURFACE_BUCKET} for item in main_cards]
    supplement_cards: list[dict[str, Any]] = []
    cards = [*main_cards, *supplement_cards]
    communities = _build_community_index(cards)
    feed_contract = _build_feed_contract()
    surface_contracts = build_mini_surface_contracts()
    serialized = json.dumps(
        {
            "categories": categories,
            "communities": communities,
            "feed_contract": feed_contract,
            "surface_contracts": surface_contracts,
            "cards": cards,
        },
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    checksum = hashlib.sha1(serialized).hexdigest()
    release_id = f"release-{checksum[:12]}"
    published_at = max((card["published_at"] for card in cards), default=None)
    return {
        "schema_version": "hotpost-mini-release/v1",
        "release_id": release_id,
        "card_count": len(cards),
        "main_card_count": len(main_cards),
        "supplement_card_count": len(supplement_cards),
        "published_at": published_at,
        "checksum": checksum,
        "feed_contract": feed_contract,
        "surface_contracts": surface_contracts,
        "categories": categories,
        "communities": communities,
        "cards": cards,
    }


def _build_community_index(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for card in cards:
        communities = _card_communities(card)
        top_community = _normalize_community_name(
            card.get("top_community")
            or ((card.get("source_module") or {}).get("top_community") if isinstance(card.get("source_module"), dict) else None)
        )
        for community in communities:
            row = rows.setdefault(
                community,
                {
                    "name": community,
                    "card_count": 0,
                    "top_card_count": 0,
                    "lanes": set(),
                    "categories": set(),
                    "latest_published_at": "",
                },
            )
            row["card_count"] += 1
            if community == top_community:
                row["top_card_count"] += 1
            if card.get("lane"):
                row["lanes"].add(str(card["lane"]))
            if card.get("source_domain_name"):
                row["categories"].add(str(card["source_domain_name"]))
            published_at = str(card.get("published_at") or "")
            if published_at > row["latest_published_at"]:
                row["latest_published_at"] = published_at

    return [
        {
            **row,
            "lanes": sorted(row["lanes"]),
            "categories": sorted(row["categories"]),
        }
        for row in sorted(rows.values(), key=lambda item: (-int(item["card_count"]), str(item["name"])))
    ]


def _card_communities(card: dict[str, Any]) -> list[str]:
    values: list[Any] = []
    source_module = card.get("source_module")
    if isinstance(source_module, dict):
        values.extend(source_module.get("primary_communities") or [])
        values.append(source_module.get("top_community"))
    values.append(card.get("top_community"))
    preview_quote = card.get("preview_quote")
    if isinstance(preview_quote, dict):
        values.append(preview_quote.get("community"))
    for quote in card.get("quotes") or []:
        if isinstance(quote, dict):
            values.append(quote.get("community"))

    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        community = _normalize_community_name(value)
        if not community or community in seen:
            continue
        seen.add(community)
        normalized.append(community)
    return normalized


def _normalize_community_name(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return raw if raw.startswith("r/") else f"r/{raw}"


def _build_feed_contract() -> dict[str, int]:
    operation_defaults = get_supply_operation_defaults()
    return {
        "initial_page_size": operation_defaults["feed_initial_page_size"],
        "max_page_size": operation_defaults["feed_max_page_size"],
    }


def _apply_homepage_shelf_mix(
    cards: list[dict[str, Any]],
    *,
    reference_time: datetime | None = None,
) -> list[dict[str, Any]]:
    same_day_cards, older_cards = _split_first_published_day_cards(cards)
    if not same_day_cards:
        return cards
    return _apply_same_day_priority_order(same_day_cards) + older_cards


def _needs_cross_day_lane_mix(cards: list[dict[str, Any]]) -> bool:
    if len(cards) < 3:
        return False
    lanes = {_snapshot_lane(card) for card in cards}
    return len(lanes) == 1


def _ensure_front_breakdown_presence(cards: list[dict[str, Any]], *, window_size: int = 30) -> list[dict[str, Any]]:
    if len(cards) <= 1:
        return cards
    front_window_size = min(window_size, len(cards))
    if any(_snapshot_lane(card) == "breakdown" for card in cards[:front_window_size]):
        return cards
    breakdown_index = next(
        (index for index, card in enumerate(cards[front_window_size:], start=front_window_size) if _snapshot_lane(card) == "breakdown"),
        None,
    )
    if breakdown_index is None:
        return cards
    replace_index = _find_front_breakdown_replacement_index(cards[:front_window_size])
    if replace_index is None:
        return cards
    repaired = list(cards)
    breakdown_card = repaired.pop(breakdown_index)
    repaired.insert(replace_index, breakdown_card)
    return repaired


def _find_front_breakdown_replacement_index(front_cards: list[dict[str, Any]]) -> Optional[int]:
    if not front_cards:
        return None
    for index in range(len(front_cards) - 1, -1, -1):
        lane = _snapshot_lane(front_cards[index])
        if lane == "breakdown":
            continue
        if index == 0 and lane == "hot":
            continue
        return index
    return None


def _apply_base_homepage_shelf_mix(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not cards:
        return cards
    rules = get_supply_rolling_publish_mix()
    window_size = min(int(rules["window_size"]), len(cards))
    if window_size <= 0:
        return cards
    breakdown_floor = int(rules["lane_targets"].get("breakdown", 0))
    selected = select_governed_window_indices(cards, window_size=window_size)
    if len(selected) < window_size:
        selected = _dedup_window_indices(cards, window_size=window_size)
    selected = _promote_hot_to_front(selected, cards=cards, window_size=window_size)
    selected = _ensure_breakdown_floor(
        selected,
        cards=cards,
        window_size=window_size,
        breakdown_floor=breakdown_floor,
    )
    selected_set = set(selected)
    ordered_window = [cards[index] for index in selected]
    ordered_window = _apply_homepage_display_order(ordered_window)
    remainder = [card for index, card in enumerate(cards) if index not in selected_set]
    return ordered_window + remainder


def _promote_same_day_published_cards(
    *,
    selected_cards: list[dict[str, Any]],
    published_cards: list[dict[str, Any]],
    reference_time: datetime | None,
) -> list[dict[str, Any]]:
    if not selected_cards:
        return []
    prioritized, remainder = _split_same_day_published_cards(published_cards, reference_time=reference_time)
    if not remainder:
        return selected_cards
    if not prioritized:
        return selected_cards
    prioritized_ids = {
        str(card.get("card_id") or "").strip()
        for card in prioritized
        if str(card.get("card_id") or "").strip()
    }
    if not prioritized_ids:
        return selected_cards
    selected_ids = {
        str(card.get("card_id") or "").strip()
        for card in selected_cards
        if str(card.get("card_id") or "").strip()
    }
    if prioritized_ids.issubset(selected_ids):
        return selected_cards
    target_total = len(selected_cards)
    merged = list(prioritized)
    seen_ids = set(prioritized_ids)
    for card in selected_cards:
        card_id = str(card.get("card_id") or "").strip()
        if card_id and card_id in seen_ids:
            continue
        merged.append(card)
        if card_id:
            seen_ids.add(card_id)
    return merged[: max(target_total, len(prioritized))]


def _split_same_day_published_cards(
    cards: list[dict[str, Any]],
    *,
    reference_time: datetime | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not cards:
        return [], []
    reference_day_key = _published_day_key(reference_time.isoformat().replace("+00:00", "Z")) if reference_time else None
    if not reference_day_key:
        latest_published = next((str(card.get("published_at") or "") for card in cards if str(card.get("published_at") or "").strip()), "")
        reference_day_key = _published_day_key(latest_published)
    if not reference_day_key:
        return [], list(cards)

    prioritized: list[dict[str, Any]] = []
    remainder: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for card in cards:
        card_id = str(card.get("card_id") or "").strip()
        if card_id and card_id in seen_ids:
            continue
        if card_id:
            seen_ids.add(card_id)
        if _published_day_key(str(card.get("published_at") or "")) == reference_day_key:
            prioritized.append(card)
            continue
        remainder.append(card)
    return prioritized, remainder


def _split_first_published_day_cards(cards: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not cards:
        return [], []
    first_day_key = next(
        (_published_day_key(str(card.get("published_at") or "")) for card in cards if str(card.get("published_at") or "").strip()),
        "",
    )
    if not first_day_key:
        return [], list(cards)
    same_day: list[dict[str, Any]] = []
    remainder: list[dict[str, Any]] = []
    for card in cards:
        if _published_day_key(str(card.get("published_at") or "")) == first_day_key:
            same_day.append(card)
            continue
        remainder.append(card)
    return same_day, remainder


def _published_day_key(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        return ""
    parsed = parse_dt(value)
    if parsed is not None:
        return parsed.astimezone(timezone.utc).date().isoformat()
    if "T" in value:
        return value.split("T", 1)[0]
    return value[:10] if len(value) >= 10 else ""


def _apply_homepage_display_order(
    cards: list[dict[str, Any]],
    *,
    candidate_window_size: int | None = None,
) -> list[dict[str, Any]]:
    if len(cards) <= 1:
        return cards
    display_window_size = min(30, len(cards))
    pool_window_size = min(candidate_window_size or display_window_size, len(cards))
    display_window = list(cards[:pool_window_size])
    reordered = _reorder_display_window(display_window)
    reordered = _repair_display_lane_runs(reordered)
    reordered = _repair_display_scope_runs(reordered)
    front = reordered[:display_window_size]
    remaining_front_counts: dict[str, int] = {}
    for card in front:
        key = _snapshot_card_key(card)
        remaining_front_counts[key] = remaining_front_counts.get(key, 0) + 1

    remainder: list[dict[str, Any]] = []
    for card in cards:
        key = _snapshot_card_key(card)
        if remaining_front_counts.get(key, 0) > 0:
            remaining_front_counts[key] -= 1
            continue
        remainder.append(card)
    return front + remainder


def _apply_same_day_priority_order(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(cards) <= 1:
        return cards

    display_window_size = min(30, len(cards))
    candidate_pool = list(cards)
    selected: list[dict[str, Any]] = []
    used_event_keys: set[str] = set()

    for lane in ("hot", "hot", "signal", "signal", "breakdown"):
        picked = _pop_display_card_with_fallback(
            candidate_pool,
            selected=selected,
            used_event_keys=used_event_keys,
            preferred_lanes=_display_lane_candidates(lane),
        )
        if picked is None:
            break
        selected.append(picked)
        used_event_keys.add(_display_event_key(picked))
        if len(selected) >= display_window_size:
            repaired_front = _repair_display_scope_runs(_repair_display_lane_runs(selected))
            return _merge_front_with_remainder(cards, repaired_front)

    while candidate_pool and len(selected) < display_window_size:
        hot_count = sum(1 for item in selected if _snapshot_lane(item) == "hot")
        signal_count = sum(1 for item in selected if _snapshot_lane(item) == "signal")
        preferred_lanes = ("signal", "hot", "breakdown") if hot_count > signal_count else ("hot", "signal", "breakdown")
        picked = _pop_display_card_with_fallback(
            candidate_pool,
            selected=selected,
            used_event_keys=used_event_keys,
            preferred_lanes=preferred_lanes,
        )
        if picked is None:
            break
        selected.append(picked)
        used_event_keys.add(_display_event_key(picked))

    if len(selected) < display_window_size:
        selected.extend(candidate_pool[: display_window_size - len(selected)])

    repaired_front = _repair_display_scope_runs(_repair_display_lane_runs(selected[:display_window_size]))
    return _merge_front_with_remainder(cards, repaired_front)


def _reorder_display_window(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(cards) < 5:
        return cards

    pool = list(cards)
    selected: list[dict[str, Any]] = []
    used_event_keys: set[str] = set()

    for lane in ("hot", "hot", "signal", "signal", "breakdown"):
        picked = _pop_display_card_with_fallback(
            pool,
            selected=selected,
            used_event_keys=used_event_keys,
            preferred_lanes=_display_lane_candidates(lane),
        )
        if picked is None:
            return cards
        selected.append(picked)
        used_event_keys.add(_display_event_key(picked))

    for _ in range(2):
        picked = _pop_display_card(pool, selected=selected, used_event_keys=used_event_keys, allowed_lanes=("hot",))
        if picked is None:
            break
        selected.append(picked)
        used_event_keys.add(_display_event_key(picked))

    while pool:
        remaining_slots = len(cards) - len(selected)
        if remaining_slots <= 0:
            break
        preferred_lanes = ("signal", "breakdown", "hot")
        picked = _pop_display_card(pool, selected=selected, used_event_keys=used_event_keys, allowed_lanes=preferred_lanes)
        if picked is None:
            selected.extend(pool)
            break
        selected.append(picked)
        used_event_keys.add(_display_event_key(picked))

    return selected


def _display_lane_candidates(primary_lane: str) -> tuple[str, ...]:
    if primary_lane == "hot":
        return ("hot", "signal", "breakdown")
    if primary_lane == "signal":
        return ("signal", "breakdown", "hot")
    if primary_lane == "breakdown":
        return ("breakdown", "signal", "hot")
    return (primary_lane,)


def _pop_display_card_with_fallback(
    pool: list[dict[str, Any]],
    *,
    selected: list[dict[str, Any]],
    used_event_keys: set[str],
    preferred_lanes: tuple[str, ...],
) -> Optional[dict[str, Any]]:
    seen: set[str] = set()
    for lane in preferred_lanes:
        if lane in seen:
            continue
        seen.add(lane)
        picked = _pop_display_card(
            pool,
            selected=selected,
            used_event_keys=used_event_keys,
            allowed_lanes=(lane,),
        )
        if picked is not None:
            return picked
    return None


def _repair_display_scope_runs(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(cards) <= 9:
        return cards
    repaired = list(cards)
    while True:
        violation_index = _find_scope_run_violation_index(repaired)
        if violation_index is None:
            return repaired
        swap_index = _find_scope_run_repair_swap_index(repaired, violation_index=violation_index)
        if swap_index is None:
            return repaired
        repaired[violation_index], repaired[swap_index] = repaired[swap_index], repaired[violation_index]


def _repair_display_lane_runs(cards: list[dict[str, Any]], *, max_run: int = 2) -> list[dict[str, Any]]:
    if len(cards) <= max_run:
        return cards
    repaired = list(cards)
    while True:
        violation_index = _find_lane_run_violation_index(repaired, max_run=max_run)
        if violation_index is None:
            return repaired
        swap_index = _find_lane_run_repair_swap_index(repaired, violation_index=violation_index)
        if swap_index is None:
            return repaired
        repaired[violation_index], repaired[swap_index] = repaired[swap_index], repaired[violation_index]


def _find_lane_run_violation_index(cards: list[dict[str, Any]], *, max_run: int) -> Optional[int]:
    run = 1
    for index in range(1, len(cards)):
        if _snapshot_lane(cards[index]) == _snapshot_lane(cards[index - 1]):
            run += 1
        else:
            run = 1
        if run > max_run:
            return index
    return None


def _find_lane_run_repair_swap_index(cards: list[dict[str, Any]], *, violation_index: int) -> Optional[int]:
    violating_lane = _snapshot_lane(cards[violation_index])
    for candidate_index in range(violation_index + 1, len(cards)):
        if _snapshot_lane(cards[candidate_index]) == violating_lane:
            continue
        swapped = list(cards)
        swapped[violation_index], swapped[candidate_index] = swapped[candidate_index], swapped[violation_index]
        next_violation = _find_lane_run_violation_index(swapped, max_run=2)
        if next_violation is not None and next_violation <= violation_index:
            continue
        return candidate_index
    return None


def _find_scope_run_violation_index(cards: list[dict[str, Any]]) -> Optional[int]:
    run = 1
    for index in range(1, len(cards)):
        current_scope = str(cards[index].get("source_scope_id") or "")
        previous_scope = str(cards[index - 1].get("source_scope_id") or "")
        if current_scope and current_scope == previous_scope:
            run += 1
        else:
            run = 1
        if index >= 9 and run > 2:
            return index
    return None


def _find_scope_run_repair_swap_index(cards: list[dict[str, Any]], *, violation_index: int) -> Optional[int]:
    protected_prefix = 9
    candidate_indices = [
        index
        for index in range(protected_prefix, len(cards))
        if index != violation_index
    ]
    candidate_indices.sort(key=lambda index: (abs(index - violation_index), index))
    violating_scope = str(cards[violation_index].get("source_scope_id") or "")
    for candidate_index in candidate_indices:
        candidate_scope = str(cards[candidate_index].get("source_scope_id") or "")
        if not candidate_scope or candidate_scope == violating_scope:
            continue
        swapped = list(cards)
        swapped[violation_index], swapped[candidate_index] = swapped[candidate_index], swapped[violation_index]
        if _find_scope_run_violation_index(swapped) is not None:
            continue
        return candidate_index
    return None


def _pop_display_card(
    pool: list[dict[str, Any]],
    *,
    selected: list[dict[str, Any]],
    used_event_keys: set[str],
    allowed_lanes: tuple[str, ...],
) ->Optional[ dict[str, Any]]:
    preferred_index = _find_display_card_index(
        pool,
        selected=selected,
        used_event_keys=used_event_keys,
        allowed_lanes=allowed_lanes,
        prefer_scope_stagger=len(selected) < 9,
        enforce_scope_limit=True,
    )
    if preferred_index is None:
        preferred_index = _find_display_card_index(
            pool,
            selected=selected,
            used_event_keys=used_event_keys,
            allowed_lanes=allowed_lanes,
            prefer_scope_stagger=False,
            enforce_scope_limit=True,
        )
    if preferred_index is None:
        preferred_index = _find_display_card_index(
            pool,
            selected=selected,
            used_event_keys=used_event_keys,
            allowed_lanes=allowed_lanes,
            prefer_scope_stagger=False,
            enforce_scope_limit=False,
        )
    if preferred_index is None:
        return None
    return pool.pop(preferred_index)


def _find_display_card_index(
    pool: list[dict[str, Any]],
    *,
    selected: list[dict[str, Any]],
    used_event_keys: set[str],
    allowed_lanes: tuple[str, ...],
    prefer_scope_stagger: bool,
    enforce_scope_limit: bool,
) ->Optional[ int]:
    previous_scope = str(selected[-1].get("source_scope_id") or "") if selected else ""
    for index, card in enumerate(pool):
        lane = _snapshot_lane(card)
        if lane not in allowed_lanes:
            continue
        event_key = _display_event_key(card)
        if event_key and event_key in used_event_keys:
            continue
        scope_id = str(card.get("source_scope_id") or "")
        if prefer_scope_stagger and previous_scope and scope_id == previous_scope:
            continue
        if enforce_scope_limit and not _scope_run_allowed(selected, scope_id):
            continue
        return index
    return None


def _scope_run_allowed(selected: list[dict[str, Any]], scope_id: str) -> bool:
    if not scope_id:
        return True
    run = 0
    for card in reversed(selected):
        if str(card.get("source_scope_id") or "") != scope_id:
            break
        run += 1
    return run < 2


def _display_event_key(card: dict[str, Any]) -> str:
    source_link = str(card.get("source_link") or "").strip()
    if source_link:
        return source_link
    title = str(card.get("title") or "").lower()
    return "".join(ch for ch in title if ch.isalnum())


def _snapshot_card_key(card: dict[str, Any]) -> str:
    card_id = str(card.get("card_id") or "").strip()
    if card_id:
        return card_id
    return _display_event_key(card)


def _merge_front_with_remainder(cards: list[dict[str, Any]], front: list[dict[str, Any]]) -> list[dict[str, Any]]:
    remaining_front_counts: dict[str, int] = {}
    for card in front:
        key = _snapshot_card_key(card)
        remaining_front_counts[key] = remaining_front_counts.get(key, 0) + 1

    remainder: list[dict[str, Any]] = []
    for card in cards:
        key = _snapshot_card_key(card)
        if remaining_front_counts.get(key, 0) > 0:
            remaining_front_counts[key] -= 1
            continue
        remainder.append(card)
    return front + remainder


def _dedup_window_indices(cards: list[dict[str, Any]], *, window_size: int) -> list[int]:
    selected: list[int] = []
    used_keys: set[tuple[str, str]] = set()
    initial_window = min(window_size, len(cards))
    for index in range(initial_window):
        key = _window_key(cards[index])
        if key in used_keys:
            continue
        selected.append(index)
        used_keys.add(key)
    for index in range(initial_window, len(cards)):
        if len(selected) >= window_size:
            break
        key = _window_key(cards[index])
        if key in used_keys:
            continue
        selected.append(index)
        used_keys.add(key)
    if len(selected) < window_size:
        selected_set = set(selected)
        for index in range(len(cards)):
            if len(selected) >= window_size:
                break
            if index in selected_set:
                continue
            selected.append(index)
            selected_set.add(index)
    return selected


def _promote_hot_to_front(selected: list[int], *, cards: list[dict[str, Any]], window_size: int) -> list[int]:
    hot_index = next((index for index in selected if _snapshot_lane(cards[index]) == "hot"), None)
    if hot_index is None:
        selected_set = set(selected)
        used_keys = {_window_key(cards[index]) for index in selected}
        hot_index = next(
            (
                index
                for index, card in enumerate(cards)
                if index not in selected_set
                and _snapshot_lane(card) == "hot"
                and _window_key(card) not in used_keys
            ),
            None,
        )
        if hot_index is None:
            return selected
        selected = selected[:-1] + [hot_index]
    selected = [index for index in selected if index != hot_index]
    return [hot_index] + selected[: max(window_size - 1, 0)]


def _ensure_breakdown_floor(
    selected: list[int],
    *,
    cards: list[dict[str, Any]],
    window_size: int,
    breakdown_floor: int,
) -> list[int]:
    if breakdown_floor <= 0 or not selected:
        return selected
    selected = list(selected[:window_size])
    selected_set = set(selected)
    used_keys = {_window_key(cards[index]) for index in selected}
    breakdown_count = sum(1 for index in selected if _snapshot_lane(cards[index]) == "breakdown")
    if breakdown_count >= breakdown_floor:
        return selected
    for candidate_index, card in enumerate(cards):
        if breakdown_count >= breakdown_floor:
            break
        if candidate_index in selected_set:
            continue
        if _snapshot_lane(card) != "breakdown":
            continue
        key = _window_key(card)
        if key in used_keys:
            continue
        replace_pos = _find_breakdown_replacement_slot(selected, cards=cards)
        if replace_pos is None:
            break
        dropped_index = selected[replace_pos]
        selected[replace_pos] = candidate_index
        selected_set.remove(dropped_index)
        selected_set.add(candidate_index)
        used_keys.remove(_window_key(cards[dropped_index]))
        used_keys.add(key)
        breakdown_count += 1
    return selected


def _find_breakdown_replacement_slot(selected: list[int], *, cards: list[dict[str, Any]]) ->Optional[ int]:
    for position in range(len(selected) - 1, -1, -1):
        lane = _snapshot_lane(cards[selected[position]])
        if lane == "breakdown":
            continue
        if position == 0 and lane == "hot":
            continue
        return position
    return None


def _snapshot_lane(card: dict[str, Any]) -> str:
    return resolve_lane(card.get("lane"), card_type=str(card.get("card_type") or "validate"))


def _window_key(card: dict[str, Any]) -> tuple[str, str]:
    return (str(card.get("source_link") or ""), _snapshot_lane(card))


def _sanitize_card_for_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    card = dict(item)
    card["lane"] = resolve_lane(card.get("lane"), card_type=str(card.get("card_type") or "validate"))
    rules = load_card_content_rules()
    _clean_card_copy(card, rules=rules)
    detail = card.get("detail")
    if isinstance(detail, dict):
        clean_detail = dict(detail)
        clean_detail.pop("min_test_action", None)
        _clean_detail_copy(clean_detail, rules=rules, lane=card.get("lane"))
        card["detail"] = clean_detail
    card = enrich_hot_controversy_chart(card)
    return card


def _clean_card_copy(card: dict[str, Any], *, rules: dict[str, Any]) -> None:
    for field_name, ensure_sentence in (
        ("title", False),
        ("summary_line", True),
        ("audience", False),
        ("why_now", True),
    ):
        value = card.get(field_name)
        if isinstance(value, str):
            card[field_name] = clean_readout_text_for_client(
                value,
                rules=rules,
                ensure_sentence=ensure_sentence,
            )


def _clean_detail_copy(detail: dict[str, Any], *, rules: dict[str, Any], lane:Optional[ str] = None) -> None:
    for field_name in validation_detail_field_names_for_payload(detail, lane=lane):
        value = detail.get(field_name)
        if isinstance(value, str):
            detail[field_name] = clean_readout_text_for_client(
                value,
                rules=rules,
                ensure_sentence=True,
            )


def publish_mini_snapshot(
    *,
    output_dir: Path,
    bundle_dir:Optional[ Path] = None,
    bundle_dirs:Optional[ list[Path]] = None,
    payload:Optional[ dict[str, Any]] = None,
    refresh_hot_controversy: bool = False,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    releases_dir = output_dir / "releases"
    releases_dir.mkdir(parents=True, exist_ok=True)
    _migrate_legacy_release_files(output_dir=output_dir, releases_dir=releases_dir)
    source_payload = _prepare_publish_payload(
        payload,
        refresh_hot_controversy=refresh_hot_controversy,
    )
    existing_latest = _load_latest_snapshot(output_dir)
    previous_cards = None
    if isinstance(existing_latest, dict):
        previous_cards = list(existing_latest.get("cards") or [])
    snapshot = build_mini_snapshot(source_payload, previous_cards=previous_cards)
    if existing_latest and existing_latest.get("checksum") == snapshot["checksum"]:
        snapshot["release_id"] = str(existing_latest.get("release_id") or snapshot["release_id"])
    release_id = snapshot["release_id"]
    version_path = releases_dir / f"{release_id}.json"
    latest_path = output_dir / "latest.json"
    manifest_path = output_dir / "manifest.json"
    _write_json(version_path, snapshot)
    _write_json(latest_path, snapshot)
    _write_json(manifest_path, _build_manifest(output_dir=output_dir, latest_snapshot=snapshot))
    cloud_db_dir = output_dir / "cloud_db"
    _write_cloud_db_seed(cloud_db_dir, snapshot)

    bundle_targets = _resolve_bundle_targets(bundle_dir=bundle_dir, bundle_dirs=bundle_dirs)
    bundled_paths: list[str] = []
    for target_dir in bundle_targets:
        target_dir.mkdir(parents=True, exist_ok=True)
        bundle_release_dir = target_dir / "releases"
        bundle_release_dir.mkdir(parents=True, exist_ok=True)
        bundle_latest_path = target_dir / "latest.json"
        bundle_manifest_path = target_dir / "manifest.json"
        bundle_version_path = bundle_release_dir / f"{release_id}.json"
        _remove_stale_release_bundles(bundle_release_dir, keep={bundle_version_path.name})
        _write_json(bundle_version_path, snapshot)
        _write_json(bundle_latest_path, snapshot)
        _write_json(bundle_manifest_path, _build_manifest(output_dir=target_dir, latest_snapshot=snapshot))
        bundled_paths.extend([str(bundle_latest_path), str(bundle_manifest_path), str(bundle_version_path)])

    return {
        "release_id": release_id,
        "card_count": snapshot["card_count"],
        "checksum": snapshot["checksum"],
        "published_at": snapshot["published_at"],
        "version_path": str(version_path),
        "latest_path": str(latest_path),
        "manifest_path": str(manifest_path),
        "cloud_db_dir": str(cloud_db_dir),
        "bundled_paths": bundled_paths,
    }


def _prepare_publish_payload(
    payload:Optional[ dict[str, Any]],
    *,
    refresh_hot_controversy: bool,
) -> dict[str, Any]:
    if payload is not None:
        source = dict(payload)
        published = [dict(item) for item in (source.get("published") or [])]
        if refresh_hot_controversy and _hot_controversy_refresh_required(published):
            published = refresh_hot_controversy_cards_sync(published)
        source["published"] = published
        return source
    categories = load_categories()
    published = load_published_cards()
    refreshed = [dict(item) for item in published]
    if refresh_hot_controversy and _hot_controversy_refresh_required(refreshed):
        refreshed = refresh_hot_controversy_cards_sync(refreshed)
        merge_published_cards(refreshed)
    return {"categories": categories, "published": refreshed}


def _hot_controversy_refresh_required(cards: list[dict[str, Any]]) -> bool:
    for card in cards:
        if str(card.get("lane") or "") != "hot" or str(card.get("card_type") or "") != "validate":
            continue
        if not isinstance(card.get("controversy_chart"), dict):
            return True
        if not isinstance(card.get("controversy_meta"), dict):
            return True
    return False


def _require_hot_controversy_ready(cards: list[dict[str, Any]]) -> None:
    missing: list[str] = []
    for card in cards:
        if str(card.get("lane") or "") != "hot" or str(card.get("card_type") or "") != "validate":
            continue
        if not isinstance(card.get("controversy_chart"), dict) or not isinstance(card.get("controversy_meta"), dict):
            missing.append(str(card.get("card_id") or "unknown-card"))
    if missing:
        raise ValueError(f"Hot validate cards missing controversy chart: {', '.join(missing)}")


def _load_latest_snapshot(output_dir: Path) ->Optional[ dict[str, Any]]:
    latest_path = output_dir / "latest.json"
    if not latest_path.exists():
        return None
    return json.loads(latest_path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _build_manifest(*, output_dir: Path, latest_snapshot: dict[str, Any]) -> dict[str, Any]:
    releases_dir = output_dir / "releases"
    deduped: dict[str, dict[str, Any]] = {}
    if releases_dir.exists():
        for path in sorted(releases_dir.glob("*.json")):
            snapshot = json.loads(path.read_text(encoding="utf-8"))
            item = {
                "release_id": snapshot["release_id"],
                "checksum": snapshot["checksum"],
                "card_count": snapshot["card_count"],
                "published_at": snapshot["published_at"],
                "path": f"releases/{path.name}",
            }
            current = deduped.get(snapshot["checksum"])
            if current is None:
                deduped[snapshot["checksum"]] = item
                continue
            if current["release_id"] == latest_snapshot["release_id"]:
                continue
            if item["release_id"] == latest_snapshot["release_id"]:
                deduped[snapshot["checksum"]] = item
                continue
            if (item["published_at"] or "", item["release_id"]) > (current["published_at"] or "", current["release_id"]):
                deduped[snapshot["checksum"]] = item
    items = list(deduped.values())
    items.sort(key=lambda item: (item["published_at"] or "", item["release_id"]), reverse=True)
    return {
        "schema_version": "hotpost-mini-release-manifest/v1",
        "latest_release_id": latest_snapshot["release_id"],
        "latest_path": "latest.json",
        "release_count": len(items),
        "releases": items,
    }


def _remove_stale_release_bundles(directory: Path, *, keep: set[str]) -> None:
    if not directory.exists():
        return
    for path in directory.glob("*.json"):
        if path.name not in keep:
            path.unlink()
    for path in directory.iterdir():
        if path.is_dir():
            shutil.rmtree(path)


def _migrate_legacy_release_files(*, output_dir: Path, releases_dir: Path) -> None:
    for path in output_dir.glob("release-*.json"):
        target = releases_dir / path.name
        if target.exists():
            path.unlink()
            continue
        shutil.move(str(path), str(target))


def _resolve_bundle_targets(*, bundle_dir:Optional[ Path], bundle_dirs:Optional[ list[Path]]) -> list[Path]:
    targets: list[Path] = []
    if bundle_dir is not None:
        targets.append(bundle_dir)
    if bundle_dirs:
        targets.extend(bundle_dirs)

    unique_targets: list[Path] = []
    seen: set[Path] = set()
    for target in targets:
        resolved = target.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_targets.append(target)
    return unique_targets


def _write_cloud_db_seed(output_dir: Path, snapshot: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    synced_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    meta_doc = {
        "schema_version": snapshot["schema_version"],
        "release_id": snapshot["release_id"],
        "card_count": snapshot["card_count"],
        "main_card_count": int(snapshot.get("main_card_count") or 0),
        "supplement_card_count": int(snapshot.get("supplement_card_count") or 0),
        "published_at": snapshot["published_at"],
        "checksum": snapshot["checksum"],
        "categories": snapshot["categories"],
        "communities": snapshot.get("communities") or [],
        "feed_contract": snapshot["feed_contract"],
        "surface_contracts": snapshot.get("surface_contracts") or {},
        "synced_at": synced_at,
    }
    card_docs = [
        {
            "release_id": snapshot["release_id"],
            "synced_at": synced_at,
            "display_order": index,
            **item,
        }
        for index, item in enumerate(snapshot["cards"])
    ]
    _write_json(output_dir / "mini_release_meta.json", [meta_doc])
    _write_json(output_dir / "mini_release_cards.json", card_docs)
    _write_jsonl(output_dir / "mini_release_meta.jsonl", [meta_doc])
    _write_jsonl(output_dir / "mini_release_cards.jsonl", card_docs)
    _write_jsonl(output_dir / "mini_release_meta.import.json", [meta_doc])
    _write_jsonl(output_dir / "mini_release_cards.import.json", card_docs)
    _write_jsonl(output_dir / "mini_release_meta.wechat-import.json", [_with_cloud_db_doc_id(meta_doc, "latest")])
    _write_jsonl(
        output_dir / "mini_release_cards.wechat-import.json",
        [_with_cloud_db_doc_id(card, str(card.get("card_id") or "")) for card in card_docs],
    )


def _with_cloud_db_doc_id(item: dict[str, Any], doc_id: str) -> dict[str, Any]:
    if not doc_id:
        raise ValueError("cloud db import doc_id must not be empty")
    return {"_id": doc_id, **item}


def _write_jsonl(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(item, ensure_ascii=False) for item in items]
    payload = "\n".join(lines)
    if payload:
        payload += "\n"
    path.write_text(payload, encoding="utf-8")
