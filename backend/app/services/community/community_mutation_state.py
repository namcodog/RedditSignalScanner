from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_category import BusinessCategory
from app.models.community_cache import CommunityCache
from app.models.community_domain_membership import CommunityDomainMembership
from app.models.community_pool import CommunityPool
from app.models.community_registry import CommunityRegistry
from app.models.community_runtime_state import CommunityRuntimeState
from app.services.community.community_category_map_service import (
    _normalize_category_keys,
)

__all__ = [
    "CommunityMutationState",
    "load_mutation_state",
    "resolve_category_keys",
    "state_is_enabled",
]


@dataclass(slots=True)
class CommunityMutationState:
    pool:Optional[ CommunityPool]
    cache:Optional[ CommunityCache]
    registry:Optional[ CommunityRegistry]
    runtime:Optional[ CommunityRuntimeState]


async def load_mutation_state(
    session: AsyncSession,
    *,
    community_name: str,
) -> CommunityMutationState:
    pool = (
        await session.execute(
            select(CommunityPool).where(CommunityPool.name == community_name)
        )
    ).scalar_one_or_none()
    cache = await session.get(CommunityCache, community_name)
    registry = (
        await session.execute(
            select(CommunityRegistry).where(
                CommunityRegistry.platform == "reddit",
                CommunityRegistry.community_name == community_name,
            )
        )
    ).scalar_one_or_none()
    runtime = await session.get(CommunityRuntimeState, registry.id) if registry else None
    return CommunityMutationState(
        pool=pool,
        cache=cache,
        registry=registry,
        runtime=runtime,
    )


async def resolve_category_keys(
    session: AsyncSession,
    *,
    raw_categories:Optional[ object],
    state: CommunityMutationState,
) -> list[str]:
    keys = await _load_active_category_keys(
        session,
        _normalize_category_keys(raw_categories),
    )
    if keys:
        return keys
    if state.registry is not None:
        rows = (
            await session.execute(
                select(CommunityDomainMembership.domain_key).where(
                    CommunityDomainMembership.community_id == state.registry.id,
                    CommunityDomainMembership.is_current.is_(True),
                )
            )
        ).scalars()
        keys = [str(row) for row in rows if row]
        if keys:
            return keys
    if state.pool is None:
        return []
    return await _load_active_category_keys(
        session,
        _normalize_category_keys(state.pool.categories),
    )


def state_is_enabled(state: CommunityMutationState) -> bool:
    if state.runtime is not None:
        return bool(state.runtime.is_enabled)
    return bool(state.pool is not None and state.pool.is_active)


async def _load_active_category_keys(
    session: AsyncSession,
    keys: list[str],
) -> list[str]:
    if not keys:
        return []
    rows = await session.execute(
        select(BusinessCategory.key).where(
            BusinessCategory.key.in_(keys),
            BusinessCategory.is_active.is_(True),
        )
    )
    allowed = {str(key) for key in rows.scalars() if key}
    return [key for key in keys if key in allowed]
