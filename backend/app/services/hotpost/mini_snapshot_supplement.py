from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.hotpost.mini_surface_contract import get_mini_supplement_surface_rules
from app.services.hotpost.topic_tree_governance_common import parse_dt


SUPPLEMENT_SURFACE_BUCKET = "supplement"
MAIN_SURFACE_BUCKET = "main"


def build_supplement_surface(
    *,
    published_cards: list[dict[str, Any]],
    main_cards: list[dict[str, Any]],
    reference_time: datetime | None = None,
) -> list[dict[str, Any]]:
    rules = get_mini_supplement_surface_rules()
    if not rules["enabled"]:
        return []

    resolved_reference = reference_time or datetime.now(timezone.utc)
    max_age_hours = int(rules["max_event_age_days"]) * 24
    max_cards = int(rules["max_cards"])
    main_card_ids = {str(item.get("card_id") or "") for item in main_cards if str(item.get("card_id") or "")}
    seen_event_keys: set[str] = set()
    selected: list[dict[str, Any]] = []

    ordered = sorted(
        published_cards,
        key=lambda item: (
            str(item.get("published_at") or ""),
            str(item.get("card_id") or ""),
        ),
        reverse=True,
    )
    for item in ordered:
        card_id = str(item.get("card_id") or "").strip()
        if not card_id or card_id in main_card_ids:
            continue
        event_at = parse_dt(item.get("source_event_at")) or parse_dt(item.get("published_at"))
        if event_at is None:
            continue
        age_hours = max((resolved_reference - event_at).total_seconds() / 3600.0, 0.0)
        if age_hours > max_age_hours:
            continue
        event_key = str(item.get("source_link") or card_id).strip().lower()
        if event_key in seen_event_keys:
            continue
        selected.append({**item, "surface_bucket": SUPPLEMENT_SURFACE_BUCKET})
        seen_event_keys.add(event_key)
        if len(selected) >= max_cards:
            break
    return selected


def build_mini_surface_contracts() -> dict[str, dict[str, Any]]:
    rules = get_mini_supplement_surface_rules()
    return {
        MAIN_SURFACE_BUCKET: {},
        SUPPLEMENT_SURFACE_BUCKET: {
            "title": rules["title"],
            "description": rules["description"],
            "initial_page_size": rules["initial_page_size"],
            "max_page_size": rules["max_page_size"],
            "max_event_age_days": rules["max_event_age_days"],
        },
    }


__all__ = [
    "MAIN_SURFACE_BUCKET",
    "SUPPLEMENT_SURFACE_BUCKET",
    "build_mini_surface_contracts",
    "build_supplement_surface",
]
