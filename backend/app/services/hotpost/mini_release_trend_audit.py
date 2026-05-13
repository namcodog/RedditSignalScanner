from __future__ import annotations

from collections import Counter
from math import ceil
from pathlib import Path
from typing import Any
import json


WATCH_COMMUNITIES = (
    "r/FacebookAds",
    "r/PPC",
    "r/BuyItForLife",
)
WATCH_PACKS = ("paid-economics",)
DEFAULT_BASELINE_RELEASE_ID = "release-727805c2aaf3"
DEFAULT_REQUIRED_NEW_RELEASES = 5
DEFAULT_FULL_COMMUNITY_CAP = 5
DEFAULT_FULL_PACK_CAP = 14
DEFAULT_FRONT_WINDOW = 30
DEFAULT_MIN_INVENTORY_CARDS = 30


def load_release_payloads(releases_dir: Path) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for path in sorted(releases_dir.glob("release-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_release_sort_timestamp"] = float(path.stat().st_mtime)
        payloads.append(payload)
    return payloads


def audit_recent_release_payloads(
    release_payloads: list[dict[str, Any]],
    *,
    front_window: int = DEFAULT_FRONT_WINDOW,
    display_limit: int = DEFAULT_REQUIRED_NEW_RELEASES,
    baseline_release_id: str = DEFAULT_BASELINE_RELEASE_ID,
    required_new_releases: int = DEFAULT_REQUIRED_NEW_RELEASES,
    inventory_minimum_cards: int = DEFAULT_MIN_INVENTORY_CARDS,
) -> dict[str, Any]:
    ordered = sorted(
        release_payloads,
        key=lambda item: (
            float(item.get("_release_sort_timestamp") or 0.0),
            str(item.get("published_at") or ""),
            str(item.get("release_id") or ""),
        ),
        reverse=True,
    )
    all_summaries = [
        _release_summary(payload, front_window=front_window)
        for payload in ordered
    ]
    _attach_trends(all_summaries)
    _attach_stability_window(
        all_summaries,
        baseline_release_id=baseline_release_id,
        required_new_releases=required_new_releases,
        inventory_minimum_cards=inventory_minimum_cards,
    )
    visible_summaries = all_summaries[: max(display_limit, 1)]
    latest = visible_summaries[0] if visible_summaries else None
    latest_stability = latest.get("stability", {}) if latest else {}
    return {
        "baseline_release_id": baseline_release_id,
        "required_new_releases": required_new_releases,
        "inventory_minimum_cards": inventory_minimum_cards,
        "release_count": len(visible_summaries),
        "total_release_count": len(all_summaries),
        "watch_communities": list(WATCH_COMMUNITIES),
        "watch_packs": list(WATCH_PACKS),
        "latest_release_id": latest["release_id"] if latest else None,
        "latest_status": latest["status"] if latest else "unknown",
        "latest_remediation_focus": latest_stability.get("remediation_focus", "inventory_only"),
        "stable_streak": int(latest_stability.get("stable_streak", 0)),
        "remaining_new_releases": max(required_new_releases - int(latest_stability.get("stable_streak", 0)), 0),
        "observed_new_releases": int(latest_stability.get("observed_new_releases", 0)),
        "release_summaries": visible_summaries,
    }


def _release_summary(payload: dict[str, Any], *, front_window: int) -> dict[str, Any]:
    cards = _main_surface_cards(payload)
    total_cards = list(payload.get("cards") or [])
    front_cards = cards[:front_window]
    full_snapshot = _layer_snapshot(cards, layer="full")
    front_snapshot = _layer_snapshot(front_cards, layer="front")
    alerts = sorted(
        set(full_snapshot["alerts"]) | set(front_snapshot["alerts"])
    )
    status = "stable" if not alerts else "watching"
    return {
        "release_id": str(payload.get("release_id") or ""),
        "published_at": str(payload.get("published_at") or ""),
        "card_count": len(cards),
        "total_card_count": len(total_cards),
        "supplement_card_count": int(payload.get("supplement_card_count") or max(len(total_cards) - len(cards), 0)),
        "front_window": len(front_cards),
        "full": full_snapshot,
        "front30": front_snapshot,
        "alerts": alerts,
        "status": status,
        "trend": {
            "community_rebounds": [],
            "pack_rebounds": [],
        },
        "stability": {
            "front30_stable": not front_snapshot["alerts"],
            "full_inventory_stable": not full_snapshot["alerts"],
            "scope_visible": False,
            "inventory_supported": False,
            "qualified_for_stable": False,
            "stable_streak": 0,
            "observed_new_releases": 0,
            "remediation_focus": "inventory_only" if not front_snapshot["alerts"] and full_snapshot["alerts"] else "release_surface",
        },
    }


def _main_surface_cards(payload: dict[str, Any]) -> list[dict[str, Any]]:
    cards = [item for item in list(payload.get("cards") or []) if isinstance(item, dict)]
    if not cards:
        return []
    if any(str(item.get("surface_bucket") or "").strip() for item in cards):
        main_cards = [item for item in cards if str(item.get("surface_bucket") or "main") == "main"]
        return main_cards or cards
    return cards


def _layer_snapshot(cards: list[dict[str, Any]], *, layer: str) -> dict[str, Any]:
    scope_counts = Counter(str(item.get("source_scope_id") or "") for item in cards if str(item.get("source_scope_id") or ""))
    community_counts = Counter(str(item.get("top_community") or "") for item in cards if str(item.get("top_community") or ""))
    pack_counts = Counter(str(item.get("topic_pack_id") or "") for item in cards if str(item.get("topic_pack_id") or ""))
    caps = _layer_caps(layer=layer, item_count=len(cards))
    over_communities = [
        name for name, count in community_counts.most_common()
        if count > caps["community"]
    ]
    over_packs = [
        name for name, count in pack_counts.most_common()
        if count > caps["pack"]
    ]
    alerts = [f"{layer}:community_over:{name}" for name in over_communities]
    alerts.extend(f"{layer}:pack_over:{name}" for name in over_packs)
    effective_watch_communities = {
        name: int(community_counts.get(name, 0))
        for name in dict.fromkeys([*WATCH_COMMUNITIES, *over_communities])
    }
    effective_watch_packs = {
        name: int(pack_counts.get(name, 0))
        for name in dict.fromkeys([*WATCH_PACKS, *over_packs])
    }

    return {
        "card_count": len(cards),
        "scope_counts": dict(scope_counts),
        "top_communities": [[name, count] for name, count in community_counts.most_common(12)],
        "top_packs": [[name, count] for name, count in pack_counts.most_common(12)],
        "watched_communities": {name: int(community_counts.get(name, 0)) for name in WATCH_COMMUNITIES},
        "watched_packs": {name: int(pack_counts.get(name, 0)) for name in WATCH_PACKS},
        "effective_watch_communities": effective_watch_communities,
        "effective_watch_packs": effective_watch_packs,
        "dynamic_watch_communities": [name for name in over_communities if name not in WATCH_COMMUNITIES],
        "dynamic_watch_packs": [name for name in over_packs if name not in WATCH_PACKS],
        "caps": caps,
        "alerts": alerts,
    }


def _layer_caps(*, layer: str, item_count: int) -> dict[str, int]:
    if layer == "front":
        return {
            "scope": max(1, ceil(max(item_count, 1) * 0.4)),
            "pack": max(2, ceil(max(item_count, 1) / 3)),
            "community": 2 if item_count >= 10 else 1 if item_count >= 4 else item_count,
        }
    return {
        "scope": max(3, ceil(max(item_count, 1) * 0.5)),
        "pack": DEFAULT_FULL_PACK_CAP,
        "community": DEFAULT_FULL_COMMUNITY_CAP,
    }


def _attach_trends(release_summaries: list[dict[str, Any]]) -> None:
    for index, current in enumerate(release_summaries):
        if index + 1 >= len(release_summaries):
            continue
        previous = release_summaries[index + 1]
        current["trend"] = {
            "community_rebounds": _rebound_names(
                current=current["full"]["effective_watch_communities"],
                previous=previous["full"]["effective_watch_communities"],
            ),
            "pack_rebounds": _rebound_names(
                current=current["full"]["effective_watch_packs"],
                previous=previous["full"]["effective_watch_packs"],
            ),
        }
        if current["trend"]["community_rebounds"] or current["trend"]["pack_rebounds"]:
            current["status"] = "rebound"


def _attach_stability_window(
    release_summaries: list[dict[str, Any]],
    *,
    baseline_release_id: str,
    required_new_releases: int,
    inventory_minimum_cards: int,
) -> None:
    baseline_index = next(
        (index for index, summary in enumerate(release_summaries) if summary["release_id"] == baseline_release_id),
        None,
    )
    if baseline_index is None:
        newer = list(release_summaries)
        baseline_summary: dict[str, Any] | None = None
    else:
        newer = release_summaries[:baseline_index]
        baseline_summary = release_summaries[baseline_index]

    stable_streak = 0
    observed_new_releases = 0
    previous_full_communities = (
        dict(baseline_summary["full"]["effective_watch_communities"])
        if baseline_summary is not None
        else {}
    )
    previous_full_packs = (
        dict(baseline_summary["full"]["effective_watch_packs"])
        if baseline_summary is not None
        else {}
    )

    for summary in reversed(newer):
        observed_new_releases += 1
        front30_stable = not summary["front30"]["alerts"]
        full_inventory_stable = not summary["full"]["alerts"]
        scope_visible = _scope_visible(summary["front30"]["scope_counts"])
        inventory_supported = int(summary["card_count"]) >= inventory_minimum_cards
        community_nonincreasing = _all_nonincreasing(
            current=summary["full"]["effective_watch_communities"],
            previous=previous_full_communities,
        )
        pack_nonincreasing = _all_nonincreasing(
            current=summary["full"]["effective_watch_packs"],
            previous=previous_full_packs,
        )
        rebound = bool(summary["trend"]["community_rebounds"] or summary["trend"]["pack_rebounds"])
        qualified = (
            front30_stable
            and full_inventory_stable
            and scope_visible
            and inventory_supported
            and community_nonincreasing
            and pack_nonincreasing
            and not rebound
        )
        if rebound:
            stable_streak = 0
            summary["status"] = "rebound"
        elif qualified:
            stable_streak += 1
            summary["status"] = "stable" if stable_streak >= required_new_releases else "watching"
        else:
            stable_streak = 0
            summary["status"] = "watching"
        summary["stability"] = {
            "front30_stable": front30_stable,
            "full_inventory_stable": full_inventory_stable,
            "scope_visible": scope_visible,
            "inventory_supported": inventory_supported,
            "community_nonincreasing": community_nonincreasing,
            "pack_nonincreasing": pack_nonincreasing,
            "qualified_for_stable": qualified,
            "stable_streak": stable_streak,
            "observed_new_releases": observed_new_releases,
            "remediation_focus": "inventory_only" if front30_stable and not full_inventory_stable else "release_surface",
        }
        previous_full_communities = dict(summary["full"]["effective_watch_communities"])
        previous_full_packs = dict(summary["full"]["effective_watch_packs"])

    if baseline_summary is not None:
        baseline_summary["status"] = "watching" if baseline_summary["alerts"] else "stable"
        baseline_summary["stability"] = {
            "front30_stable": not baseline_summary["front30"]["alerts"],
            "full_inventory_stable": not baseline_summary["full"]["alerts"],
            "scope_visible": _scope_visible(baseline_summary["front30"]["scope_counts"]),
            "inventory_supported": int(baseline_summary["card_count"]) >= inventory_minimum_cards,
            "qualified_for_stable": False,
            "stable_streak": 0,
            "observed_new_releases": 0,
            "remediation_focus": "inventory_only" if not baseline_summary["front30"]["alerts"] and baseline_summary["full"]["alerts"] else "release_surface",
        }

    if release_summaries and release_summaries[0]["release_id"] == baseline_release_id and baseline_summary is not None:
        release_summaries[0]["status"] = "watching"

    if release_summaries:
        latest = release_summaries[0]
        latest_stability = latest.setdefault("stability", {})
        latest_stability["stable_streak"] = int(latest_stability.get("stable_streak", stable_streak if newer else 0))
        latest_stability["observed_new_releases"] = observed_new_releases


def _scope_visible(scope_counts: dict[str, int]) -> bool:
    required = {"ai-automation", "business-growth-ops", "ecommerce-sellers"}
    return required.issubset({name for name, count in scope_counts.items() if int(count) > 0})


def _all_nonincreasing(*, current: dict[str, int], previous: dict[str, int]) -> bool:
    for name, value in current.items():
        if int(value) > int(previous.get(name, 0)):
            return False
    return True


def _rebound_names(*, current: dict[str, int], previous: dict[str, int]) -> list[str]:
    names: list[str] = []
    for name, value in current.items():
        if value > int(previous.get(name, 0)):
            names.append(name)
    return names


__all__ = [
    "WATCH_COMMUNITIES",
    "WATCH_PACKS",
    "DEFAULT_BASELINE_RELEASE_ID",
    "DEFAULT_REQUIRED_NEW_RELEASES",
    "DEFAULT_FRONT_WINDOW",
    "DEFAULT_FULL_COMMUNITY_CAP",
    "DEFAULT_FULL_PACK_CAP",
    "DEFAULT_MIN_INVENTORY_CARDS",
    "audit_recent_release_payloads",
    "load_release_payloads",
]
