from __future__ import annotations

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.admin_community_pool import (
    list_community_pool,
    list_discovered,
    approve_community,
    reject_community,
    disable_community,
    ApproveRequest,
    RejectRequest,
)
from app.core.security import TokenPayload
from sqlalchemy import select
from app.models.community_pool import CommunityPool
from app.models.discovered_community import DiscoveredCommunity
from app.models.user import User


from app.core.security import hash_password



@pytest.mark.asyncio
async def test_unit_list_endpoints_cover_lines(db_session: AsyncSession) -> None:
    payload = TokenPayload(sub=str(uuid.uuid4()))

    # Should execute query and return empty items
    body1 = await list_community_pool(payload=payload, session=db_session)
    assert body1["code"] == 0
    assert isinstance(body1["data"]["items"], list)

    body2 = await list_discovered(payload=payload, session=db_session)
    assert body2["code"] == 0
    assert isinstance(body2["data"]["items"], list)


@pytest.mark.asyncio
async def test_unit_error_branches_approve_and_reject(db_session: AsyncSession) -> None:
    good_payload = TokenPayload(sub=str(uuid.uuid4()))
    bad_payload = TokenPayload(sub="not-a-uuid")

    # approve 404 when pending missing
    with pytest.raises(Exception):
        await approve_community(
            body=ApproveRequest(name="r/not_exist"),
            payload=good_payload,
            session=db_session,
        )

    # approve 401 when token subject invalid
    with pytest.raises(Exception):
        await approve_community(
            body=ApproveRequest(name="r/not_exist"),
            payload=bad_payload,
            session=db_session,
        )

    # reject 404 when pending missing
    with pytest.raises(Exception):
        await reject_community(
            body=RejectRequest(name="r/not_exist"),
            payload=good_payload,
            session=db_session,
        )

    # reject 401 when token subject invalid
    with pytest.raises(Exception):
        await reject_community(
            body=RejectRequest(name="r/not_exist"),
            payload=bad_payload,
            session=db_session,
        )


@pytest.mark.asyncio
async def test_unit_disable_community_404(db_session: AsyncSession) -> None:
    payload = TokenPayload(sub=str(uuid.uuid4()))
    with pytest.raises(Exception):
        await disable_community(name="r/not_exist", payload=payload, session=db_session)



@pytest.mark.asyncio
async def test_unit_approve_success_flow(db_session: AsyncSession) -> None:
    good_payload = TokenPayload(sub=str(uuid.uuid4()))
    # ensure reviewer exists per FK
    reviewer = User(id=uuid.UUID(good_payload.sub), email="admin@example.com", password_hash=hash_password("testpass123"))
    db_session.add(reviewer)
    await db_session.commit()

    # prepare pending
    from datetime import datetime, timezone
    pending = DiscoveredCommunity(
        name="r/unit_pending",
        status="pending",
        discovered_from_keywords={"keywords": ["k1", "k2"]},
        discovered_count=2,
        first_discovered_at=datetime.now(timezone.utc),
        last_discovered_at=datetime.now(timezone.utc),
    )
    db_session.add(pending)
    await db_session.commit()

    body = await approve_community(
        body=ApproveRequest(name="r/unit_pending", tier="medium"),
        payload=good_payload,
        session=db_session,
    )
    assert body["code"] == 0
    # verify db changed
    pool = (
        await db_session.execute(select(CommunityPool).where(CommunityPool.name == "r/unit_pending"))
    ).scalar_one()
    assert pool.is_active is True


@pytest.mark.asyncio
async def test_unit_reject_success_flow(db_session: AsyncSession) -> None:
    good_payload = TokenPayload(sub=str(uuid.uuid4()))
    # ensure reviewer exists per FK
    reviewer = User(id=uuid.UUID(good_payload.sub), email="admin2@example.com", password_hash=hash_password("testpass123"))
    db_session.add(reviewer)
    await db_session.commit()

    # prepare pending
    from datetime import datetime, timezone
    pending = DiscoveredCommunity(
        name="r/unit_reject",
        status="pending",
        discovered_from_keywords=None,
        discovered_count=0,
        first_discovered_at=datetime.now(timezone.utc),
        last_discovered_at=datetime.now(timezone.utc),
    )
    db_session.add(pending)
    await db_session.commit()

    body = await reject_community(
        body=RejectRequest(name="r/unit_reject"),
        payload=good_payload,
        session=db_session,
    )
    assert body["code"] == 0


@pytest.mark.asyncio
async def test_unit_disable_success_flow(db_session: AsyncSession) -> None:
    good_payload = TokenPayload(sub=str(uuid.uuid4()))
    reviewer = User(id=uuid.UUID(good_payload.sub), email="admin-disable@example.com", password_hash=hash_password("testpass123"))
    db_session.add(reviewer)
    await db_session.commit()
    # prepare pool
    pool = CommunityPool(
        name="r/unit_disable",
        tier="low",
        categories={},
        description_keywords={"keywords": []},
        daily_posts=0,
        avg_comment_length=0,
        quality_score=0.1,
        priority="low",
        user_feedback_count=0,
        discovered_count=0,
        is_active=True,
    )
    db_session.add(pool)
    await db_session.commit()

    body = await disable_community(name="r/unit_disable", payload=good_payload, session=db_session)
    assert body["code"] == 0
    db_session.expire_all()
    stored = (
        await db_session.execute(select(CommunityPool).where(CommunityPool.name == "r/unit_disable"))
    ).scalar_one()
    assert stored.is_active is False
