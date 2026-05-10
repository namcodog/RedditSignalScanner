from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_cache import CommunityCache
from app.models.community_domain_membership import CommunityDomainMembership
from app.models.community_governance_decision import CommunityGovernanceDecision
from app.models.community_pool import CommunityPool
from app.models.community_registry import CommunityRegistry
from app.models.community_runtime_state import CommunityRuntimeState
from app.services.community.truth_source_reconciler import reconcile_legacy_truth


@dataclass(slots=True)
class TruthSourceSyncResult:
    community_name: str
    registry_id: int
    memberships_written: int
    governance_written: int
    runtime_state_written: bool


async def _load_valid_domain_keys(
    session: AsyncSession,
    *,
    requested_keys: list[str],
) -> set[str]:
    if not requested_keys:
        return set()
    result = await session.execute(
        text(
            """
            SELECT key
            FROM business_categories
            WHERE is_active = true
              AND key = ANY(CAST(:keys AS text[]))
            """
        ),
        {"keys": requested_keys},
    )
    return {str(row[0]) for row in result.fetchall()}


async def _upsert_registry(
    session: AsyncSession,
    *,
    payload: dict,
) -> CommunityRegistry:
    stmt = select(CommunityRegistry).where(
        CommunityRegistry.platform == payload["platform"],
        CommunityRegistry.community_name == payload["community_name"],
    )
    registry = (await session.execute(stmt)).scalar_one_or_none()
    if registry is None:
        registry = CommunityRegistry(**payload)
        session.add(registry)
    else:
        for field, value in payload.items():
            setattr(registry, field, value)
    await session.flush()
    return registry


async def _sync_memberships(
    session: AsyncSession,
    *,
    registry_id: int,
    payloads: list[dict],
) -> tuple[dict[str, CommunityDomainMembership], int]:
    valid_keys = await _load_valid_domain_keys(
        session,
        requested_keys=[payload["domain_key"] for payload in payloads],
    )
    existing_rows = (
        await session.execute(
            select(CommunityDomainMembership).where(
                CommunityDomainMembership.community_id == registry_id
            )
        )
    ).scalars()
    existing = {row.domain_key: row for row in existing_rows}
    active_keys: set[str] = set()
    written = 0

    for payload in payloads:
        domain_key = payload["domain_key"]
        if domain_key not in valid_keys:
            continue
        active_keys.add(domain_key)
        row = existing.get(domain_key)
        values = dict(payload)
        values["community_id"] = registry_id
        if row is None:
            row = CommunityDomainMembership(**values)
            session.add(row)
            existing[domain_key] = row
        else:
            for field, value in values.items():
                setattr(row, field, value)
        written += 1

    for domain_key, row in existing.items():
        if domain_key in active_keys:
            continue
        row.is_current = False
        row.is_primary = False

    await session.flush()
    return {key: row for key, row in existing.items() if row.is_current}, written


async def _sync_governance(
    session: AsyncSession,
    *,
    memberships: dict[str, CommunityDomainMembership],
    payloads: list[dict],
) -> int:
    written = 0
    current_rows = (
        await session.execute(
            select(CommunityGovernanceDecision).where(
                CommunityGovernanceDecision.membership_id.in_(
                    [row.id for row in memberships.values()]
                ),
                CommunityGovernanceDecision.is_current.is_(True),
            )
        )
    ).scalars()
    current_by_membership = {row.membership_id: row for row in current_rows}

    for payload in payloads:
        membership = memberships.get(payload["domain_key"])
        if membership is None:
            continue
        current = current_by_membership.get(membership.id)
        same_as_current = (
            current is not None
            and current.decision == payload["decision"]
            and current.reason_code == payload["reason_code"]
            and current.notes == payload["notes"]
            and current.decided_by == payload.get("decided_by")
        )
        if same_as_current:
            current.evidence = payload["evidence"]
            current.decided_at = payload["decided_at"]
            current.decided_by = payload.get("decided_by")
            written += 1
            continue
        if current is not None:
            current.is_current = False
        row = CommunityGovernanceDecision(
            membership_id=membership.id,
            decision=payload["decision"],
            reason_code=payload["reason_code"],
            notes=payload["notes"],
            evidence=payload["evidence"],
            decided_at=payload["decided_at"],
            decided_by=payload.get("decided_by"),
            is_current=True,
        )
        session.add(row)
        written += 1

    await session.flush()
    return written


async def _sync_runtime_state(
    session: AsyncSession,
    *,
    registry_id: int,
    payload:Optional[ dict],
) -> bool:
    if payload is None:
        return False
    row = await session.get(CommunityRuntimeState, registry_id)
    values = dict(payload)
    values["community_id"] = registry_id
    if row is None:
        row = CommunityRuntimeState(**values)
        session.add(row)
    else:
        for field, value in values.items():
            setattr(row, field, value)
    await session.flush()
    return True


async def sync_legacy_truth_for_community(
    session: AsyncSession,
    *,
    pool:Optional[ CommunityPool],
    cache:Optional[ CommunityCache],
) -> TruthSourceSyncResult:
    """Bootstrap/repair helper only.

    正式社区运营链已经是 truth -> projection，这里只给 restore/recovery 用，
    用来把可信 legacy 快照一次性重建到 truth-source。
    """
    reconciled = reconcile_legacy_truth(pool=pool, cache=cache)
    registry = await _upsert_registry(session, payload=reconciled.registry)
    memberships, membership_count = await _sync_memberships(
        session,
        registry_id=registry.id,
        payloads=reconciled.memberships,
    )
    governance_count = await _sync_governance(
        session,
        memberships=memberships,
        payloads=reconciled.governance,
    )
    runtime_written = await _sync_runtime_state(
        session,
        registry_id=registry.id,
        payload=reconciled.runtime_state,
    )
    return TruthSourceSyncResult(
        community_name=registry.community_name,
        registry_id=registry.id,
        memberships_written=membership_count,
        governance_written=governance_count,
        runtime_state_written=runtime_written,
    )


__all__ = ["TruthSourceSyncResult", "sync_legacy_truth_for_community"]
