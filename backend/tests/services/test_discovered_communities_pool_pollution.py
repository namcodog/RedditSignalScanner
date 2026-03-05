from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.models.discovered_community import DiscoveredCommunity
from app.models.task import Task
from app.models.user import User
from app.services.analysis.analysis_engine import (
    CollectedCommunity,
    CommunityProfile,
    _record_discovered_communities,
)


@pytest.mark.asyncio
async def test_record_discovered_communities_does_not_activate_pool_rows() -> None:
    """
    Guardrail: discovery results must NOT pollute the official community pool.

    The FK from discovered_communities.name -> community_pool.name requires the pool
    row to exist, but it must be inserted as:
    - tier=candidate
    - is_active=false
    - status is not relied upon (is_active=false is the hard gate)
    """

    name = "r/test_discovered_pollution_guard"

    async with SessionFactory() as session:
        # Must satisfy ck_users_password_hash_format (bcrypt or pbkdf2 prefix)
        user = User(
            email="pollution-guard@example.com",
            password_hash="$2b$12$dummy",
        )
        session.add(user)
        await session.flush()

        task = Task(
            user_id=user.id,
            product_description="Pollution guard task (long enough for constraints)",
        )
        session.add(task)
        await session.commit()
        task_id = task.id

    profile = CommunityProfile(
        name=name,
        categories=[],
        description_keywords=[],
        daily_posts=0,
        avg_comment_length=0,
        cache_hit_rate=0.0,
    )
    collected = [
        CollectedCommunity(
            profile=profile,
            posts=[{"id": "t3_dummy"}],  # mention_count > 0
            cache_hits=0,
            cache_misses=0,
        )
    ]

    await _record_discovered_communities(task_id=task_id, collected=collected, keywords=["e2e"])

    async with SessionFactory() as session:
        pool_row = (
            await session.execute(select(CommunityPool).where(CommunityPool.name == name))
        ).scalar_one()
        assert pool_row.tier == "candidate"
        assert pool_row.is_active is False

        discovered_row = (
            await session.execute(
                select(DiscoveredCommunity).where(DiscoveredCommunity.name == name)
            )
        ).scalar_one()
        assert discovered_row.status == "pending"
        assert discovered_row.discovered_from_task_id == task_id
