from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any

from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.community.community_category_map_service import _normalize_category_keys


def _as_float(value: Any) ->Optional[ float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_scalar(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def normalize_community_name(name:Optional[ str]) -> str:
    raw = str(name or "").strip()
    if not raw:
        raise ValueError("community name is required")
    return raw if raw.lower().startswith("r/") else f"r/{raw}"


@dataclass(slots=True)
class ReconciledCommunityTruth:
    registry: dict[str, Any]
    memberships: list[dict[str, Any]]
    governance: list[dict[str, Any]]
    runtime_state:Optional[ dict[str, Any]]


def _build_registry_payload(
    *,
    pool:Optional[ CommunityPool],
    cache:Optional[ CommunityCache],
) -> dict[str, Any]:
    name = normalize_community_name(
        getattr(pool, "name", None) or getattr(cache, "community_name", None)
    )
    return {
        "platform": "reddit",
        "community_name": name,
        "display_name": name.replace("r/", "", 1),
        "canonical_url": f"https://www.reddit.com/{name}",
        "legacy_pool_id": getattr(pool, "id", None),
        "source_of_truth": "reconciled",
        "is_enabled": bool(
            getattr(pool, "is_active", True) and getattr(cache, "is_active", True)
        ),
        "first_seen_at": None,
        "last_seen_at": getattr(cache, "last_seen_created_at", None),
    }


def _build_membership_payloads(pool:Optional[ CommunityPool]) -> list[dict[str, Any]]:
    if pool is None:
        return []

    categories = _normalize_category_keys(getattr(pool, "categories", None))
    if not categories:
        return []

    confidence = _as_float(getattr(pool, "quality_score", None))
    payloads: list[dict[str, Any]] = []
    for index, category in enumerate(categories):
        payloads.append(
            {
                "domain_key": category,
                "membership_source": "reconciled",
                "confidence": confidence,
                "is_primary": index == 0,
                "is_current": True,
                "evidence": {
                    "legacy_pool_id": getattr(pool, "id", None),
                    "legacy_priority": getattr(pool, "priority", None),
                },
                "notes": "reconciled from community_pool.categories",
            }
        )
    return payloads


def _build_governance_payloads(
    pool:Optional[ CommunityPool],
    *,
    memberships: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if pool is None or not memberships:
        return []

    if getattr(pool, "is_blacklisted", False):
        decision = "blocked"
        reason_code = "legacy_blacklist"
    elif getattr(pool, "is_active", False):
        decision = "approved"
        reason_code = "legacy_active"
    else:
        decision = "review"
        reason_code = "legacy_inactive"

    decided_at = getattr(pool, "last_evaluated_at", None) or getattr(
        pool, "updated_at", None
    )
    payloads: list[dict[str, Any]] = []
    for membership in memberships:
        payloads.append(
            {
                "decision": decision,
                "reason_code": reason_code,
                "notes": getattr(pool, "blacklist_reason", None),
                "evidence": {
                    "legacy_pool_id": getattr(pool, "id", None),
                    "legacy_health_status": getattr(pool, "health_status", None),
                },
                "decided_at": decided_at or datetime.utcnow(),
                "is_current": True,
                "domain_key": membership["domain_key"],
            }
        )
    return payloads


def _build_runtime_state_payload(cache:Optional[ CommunityCache]) ->Optional[ dict[str, Any]]:
    if cache is None:
        return None

    backfill_status = str(getattr(cache, "backfill_status", "") or "").upper()
    if not getattr(cache, "is_active", False):
        crawl_status = "paused"
    elif backfill_status in {"NEEDS", "RUNNING"}:
        crawl_status = "needs_backfill"
    else:
        crawl_status = "active"

    return {
        "crawl_status": crawl_status,
        "crawl_priority": int(getattr(cache, "crawl_priority", 50) or 50),
        "is_enabled": bool(getattr(cache, "is_active", True)),
        "legacy_cache_name": getattr(cache, "community_name", None),
        "member_count": getattr(cache, "member_count", None),
        "sample_posts": int(getattr(cache, "sample_posts", 0) or 0),
        "sample_comments": int(getattr(cache, "sample_comments", 0) or 0),
        "last_crawled_at": getattr(cache, "last_crawled_at", None),
        "last_attempt_at": getattr(cache, "last_attempt_at", None),
        "last_seen_post_at": getattr(cache, "last_seen_created_at", None),
        "backfill_floor": getattr(cache, "backfill_floor", None),
        "runtime_notes": {
            "backfill_status": _json_scalar(getattr(cache, "backfill_status", None)),
            "coverage_months": _json_scalar(getattr(cache, "coverage_months", None)),
            "backfill_capped": _json_scalar(getattr(cache, "backfill_capped", None)),
            "backfill_cursor": _json_scalar(getattr(cache, "backfill_cursor", None)),
            "backfill_cursor_created_at": _json_scalar(
                getattr(cache, "backfill_cursor_created_at", None)
            ),
            "backfill_updated_at": _json_scalar(
                getattr(cache, "backfill_updated_at", None)
            ),
            "avg_valid_posts": int(getattr(cache, "avg_valid_posts", 0) or 0),
            "quality_tier": _json_scalar(getattr(cache, "quality_tier", None)),
        },
    }


def reconcile_legacy_truth(
    *,
    pool:Optional[ CommunityPool],
    cache:Optional[ CommunityCache],
) -> ReconciledCommunityTruth:
    registry = _build_registry_payload(pool=pool, cache=cache)
    memberships = _build_membership_payloads(pool)
    governance = _build_governance_payloads(pool, memberships=memberships)
    runtime_state = _build_runtime_state_payload(cache)
    return ReconciledCommunityTruth(
        registry=registry,
        memberships=memberships,
        governance=governance,
        runtime_state=runtime_state,
    )


__all__ = [
    "ReconciledCommunityTruth",
    "normalize_community_name",
    "reconcile_legacy_truth",
]
