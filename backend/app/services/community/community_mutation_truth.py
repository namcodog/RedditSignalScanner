from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_runtime_state import CommunityRuntimeState
from app.services.community.community_mutation_projection import (
    priority_to_runtime_priority,
)
from app.services.community.truth_source_sync_service import (
    _sync_governance,
    _sync_memberships,
    _sync_runtime_state,
)

__all__ = ["sync_truth_memberships", "sync_truth_runtime"]


async def sync_truth_memberships(
    session: AsyncSession,
    *,
    registry_id: int,
    category_keys: list[str],
    decision: str,
    actor_id: uuid.Optional[UUID],
    now: datetime,
    notes:Optional[ str],
    reason_code:Optional[ str],
) -> list[str]:
    if not category_keys:
        return []
    memberships, _ = await _sync_memberships(
        session,
        registry_id=registry_id,
        payloads=[
            {
                "domain_key": key,
                "membership_source": "manual",
                "confidence": Decimal("1.000"),
                "is_primary": index == 0,
                "is_current": True,
                "evidence": {"source": "community_mutation_service"},
                "notes": notes,
            }
            for index, key in enumerate(category_keys)
        ],
    )
    await _sync_governance(
        session,
        memberships=memberships,
        payloads=[
            {
                "domain_key": key,
                "decision": decision,
                "reason_code": reason_code,
                "notes": notes,
                "evidence": {"source": "community_mutation_service"},
                "decided_at": now,
                "decided_by": actor_id,
            }
            for key in category_keys
        ],
    )
    return category_keys


async def sync_truth_runtime(
    session: AsyncSession,
    *,
    registry_id: int,
    community_name: str,
    existing_runtime:Optional[ CommunityRuntimeState],
    runtime_enabled: bool,
    priority:Optional[ str],
) -> None:
    runtime_notes = dict(getattr(existing_runtime, "runtime_notes", {}) or {})
    backfill_status = str(runtime_notes.get("backfill_status") or "").upper()
    if not runtime_enabled:
        crawl_status = "paused"
    elif getattr(existing_runtime, "last_crawled_at", None) is None or backfill_status in {
        "NEEDS",
        "RUNNING",
        "ERROR",
    }:
        crawl_status = "needs_backfill"
    else:
        crawl_status = "active"
    await _sync_runtime_state(
        session,
        registry_id=registry_id,
        payload={
            "crawl_status": crawl_status,
            "crawl_priority": priority_to_runtime_priority(priority),
            "is_enabled": runtime_enabled,
            "legacy_cache_name": community_name,
            "member_count": getattr(existing_runtime, "member_count", None),
            "sample_posts": int(getattr(existing_runtime, "sample_posts", 0) or 0),
            "sample_comments": int(getattr(existing_runtime, "sample_comments", 0) or 0),
            "last_crawled_at": getattr(existing_runtime, "last_crawled_at", None),
            "last_attempt_at": getattr(existing_runtime, "last_attempt_at", None),
            "last_seen_post_at": getattr(existing_runtime, "last_seen_post_at", None),
            "backfill_floor": getattr(existing_runtime, "backfill_floor", None),
            "runtime_notes": runtime_notes,
        },
    )
