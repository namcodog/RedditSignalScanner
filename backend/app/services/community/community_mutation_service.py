from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.community.community_category_map_service import (
    replace_community_category_map,
)
from app.services.community.community_mutation_projection import sync_cache_projection, sync_pool_projection
from app.services.community.community_mutation_state import (
    load_mutation_state,
    resolve_category_keys,
    state_is_enabled,
)
from app.services.community.truth_source_sync_service import (
    _upsert_registry,
)
from app.services.community.community_mutation_truth import (
    sync_truth_memberships,
    sync_truth_runtime,
)

__all__ = ["CommunityMutationResult", "CommunityMutationService"]


@dataclass(slots=True)
class CommunityMutationResult:
    community_name: str
    registry_id: int
    decision: str
    runtime_enabled: bool
    categories: list[str]


class CommunityMutationService:
    """Canonical write entry for community add/remove/update operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_effective_community(
        self,
        *,
        community_name: str,
        categories:Optional[ object],
        tier: str,
        priority: str,
        description_keywords:Optional[ object],
        quality_score:Optional[ float],
        discovered_count:Optional[ int],
        actor_id: uuid.Optional[UUID],
        source_of_truth: str,
        notes:Optional[ str] = None,
    ) -> CommunityMutationResult:
        return await self._mutate(
            community_name=community_name,
            categories=categories,
            tier=tier,
            priority=priority,
            description_keywords=description_keywords,
            quality_score=quality_score,
            discovered_count=discovered_count,
            actor_id=actor_id,
            source_of_truth=source_of_truth,
            decision="approved",
            reason_code=None,
            notes=notes,
            runtime_enabled=True,
        )

    async def archive_community(
        self,
        *,
        community_name: str,
        actor_id: uuid.Optional[UUID],
        reason_code: str,
        notes:Optional[ str] = None,
    ) -> CommunityMutationResult:
        return await self._mutate(
            community_name=community_name,
            categories=None,
            tier=None,
            priority=None,
            description_keywords=None,
            quality_score=None,
            discovered_count=None,
            actor_id=actor_id,
            source_of_truth="manual",
            decision="archived",
            reason_code=reason_code,
            notes=notes,
            runtime_enabled=False,
        )

    async def sync_existing_community_settings(
        self,
        *,
        community_name: str,
        tier:Optional[ str],
        priority:Optional[ str],
        is_active:Optional[ bool],
        actor_id: uuid.Optional[UUID],
        notes:Optional[ str] = None,
    ) -> CommunityMutationResult:
        state = await load_mutation_state(self._session, community_name=community_name)
        if state.pool is None and state.registry is None:
            raise ValueError(f"community not found: {community_name}")
        enabled = is_active if is_active is not None else state_is_enabled(state)
        decision = "approved" if enabled else "archived"
        return await self._mutate(
            community_name=community_name,
            categories=None,
            tier=tier,
            priority=priority,
            description_keywords=None,
            quality_score=None,
            discovered_count=None,
            actor_id=actor_id,
            source_of_truth=(
                state.registry.source_of_truth if state.registry is not None else "manual"
            ),
            decision=decision,
            reason_code="batch_update" if not enabled else None,
            notes=notes,
            runtime_enabled=enabled,
        )

    async def _mutate(
        self,
        *,
        community_name: str,
        categories:Optional[ object],
        tier:Optional[ str],
        priority:Optional[ str],
        description_keywords:Optional[ object],
        quality_score:Optional[ float],
        discovered_count:Optional[ int],
        actor_id: uuid.Optional[UUID],
        source_of_truth: str,
        decision: str,
        reason_code:Optional[ str],
        notes:Optional[ str],
        runtime_enabled: bool,
    ) -> CommunityMutationResult:
        now = datetime.now(timezone.utc)
        state = await load_mutation_state(self._session, community_name=community_name)
        category_keys = await resolve_category_keys(
            self._session,
            raw_categories=categories,
            state=state,
        )
        if decision == "approved" and not category_keys:
            raise ValueError("effective community requires at least one valid category")

        registry = await _upsert_registry(
            self._session,
            payload={
                "platform": "reddit",
                "community_name": community_name,
                "display_name": community_name,
                "canonical_url": f"https://www.reddit.com/{community_name}",
                "legacy_pool_id": state.pool.id if state.pool is not None else None,
                "source_of_truth": source_of_truth,
                # registry 只表示“身份是否存在”，停抓/归档由 governance + runtime 表达。
                "is_enabled": True,
                "first_seen_at": (
                    state.registry.first_seen_at if state.registry is not None else now
                ),
                "last_seen_at": now,
            },
        )

        memberships = await sync_truth_memberships(
            self._session,
            registry_id=registry.id,
            category_keys=category_keys,
            decision=decision,
            actor_id=actor_id,
            now=now,
            notes=notes,
            reason_code=reason_code,
        )
        await sync_truth_runtime(
            self._session,
            registry_id=registry.id,
            community_name=community_name,
            existing_runtime=state.runtime,
            runtime_enabled=runtime_enabled,
            priority=priority or getattr(state.pool, "priority", None),
        )
        pool = await sync_pool_projection(
            self._session,
            state=state,
            community_name=community_name,
            category_keys=category_keys,
            tier=tier,
            priority=priority,
            description_keywords=description_keywords,
            quality_score=quality_score,
            discovered_count=discovered_count,
            actor_id=actor_id,
            runtime_enabled=runtime_enabled,
            now=now,
        )
        if category_keys:
            await replace_community_category_map(
                self._session,
                community_id=pool.id,
                categories=category_keys,
            )
        registry.legacy_pool_id = pool.id
        await sync_cache_projection(
            self._session,
            existing_cache=state.cache,
            community_name=community_name,
            priority=pool.priority,
            quality_score=float(pool.quality_score),
            runtime_enabled=runtime_enabled,
            now=now,
        )
        await self._session.flush()
        return CommunityMutationResult(
            community_name=community_name,
            registry_id=registry.id,
            decision=decision,
            runtime_enabled=runtime_enabled,
            categories=memberships,
        )
