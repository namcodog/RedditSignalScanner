from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.main import app
from app.models.community_pool import CommunityPool, PendingCommunity


def _override_admin_settings(admin_email: str) -> Settings:
    base = get_settings()
    return base.model_copy(update={"admin_emails_raw": admin_email})


@pytest.mark.asyncio
async def test_non_admin_forbidden_on_all_endpoints(
    client: AsyncClient, token_factory
) -> None:
    # Configure admin allowlist to a different email
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = _override_admin_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        token, _ = await token_factory(email=f"user-{uuid.uuid4().hex}@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # All endpoints should reject with 403 for non-admin
        resp1 = await client.get("/api/admin/communities/pool", headers=headers)
        resp2 = await client.get("/api/admin/communities/discovered", headers=headers)
        resp3 = await client.post("/api/admin/communities/approve", headers=headers, json={"name": "r/x"})
        resp4 = await client.post("/api/admin/communities/reject", headers=headers, json={"name": "r/x"})
        resp5 = await client.delete("/api/admin/communities/r/x", headers=headers)

        assert resp1.status_code == 403
        assert resp2.status_code == 403
        assert resp3.status_code == 403
        assert resp4.status_code == 403
        assert resp5.status_code == 403
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_list_pool_and_discovered_success(
    client: AsyncClient,
    token_factory,
    db_session: AsyncSession,
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = _override_admin_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        admin_token, _ = await token_factory(email=admin_email)
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Seed community pool
        pool = CommunityPool(
            name="r/pool_ok",
            tier="gold",
            categories={"topic": ["startup"]},
            description_keywords={"keywords": ["founder"]},
            daily_posts=100,
            avg_comment_length=50,
            quality_score=0.8,
            priority="high",
            user_feedback_count=2,
            discovered_count=5,
            is_active=True,
        )
        db_session.add(pool)

        # Seed pending/discovered
        now = datetime.now(timezone.utc)
        pending = PendingCommunity(
            name="r/discovered_ok",
            discovered_from_keywords={"keywords": ["ai", "product"]},
            discovered_count=3,
            first_discovered_at=now,
            last_discovered_at=now,
            status="pending",
            admin_reviewed_at=None,
            admin_notes=None,
            discovered_from_task_id=None,
            reviewed_by=None,
        )
        db_session.add(pending)
        await db_session.commit()

        resp_pool = await client.get("/api/admin/communities/pool", headers=headers)
        assert resp_pool.status_code == 200
        body_pool = resp_pool.json()
        assert body_pool["code"] == 0
        assert body_pool["data"]["total"] >= 1
        names = [item["name"] for item in body_pool["data"]["items"]]
        assert "r/pool_ok" in names

        resp_disc = await client.get("/api/admin/communities/discovered", headers=headers)
        assert resp_disc.status_code == 200
        body_disc = resp_disc.json()
        assert body_disc["code"] == 0
        disc_names = [item["name"] for item in body_disc["data"]["items"]]
        assert "r/discovered_ok" in disc_names
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_approve_creates_or_updates_pool_and_marks_pending_approved(
    client: AsyncClient,
    token_factory,
    db_session: AsyncSession,
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = _override_admin_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        admin_token, admin_user_id = await token_factory(email=admin_email)
        headers = {"Authorization": f"Bearer {admin_token}"}

        now = datetime.now(timezone.utc)
        db_session.add(
            PendingCommunity(
                name="r/approve_me",
                discovered_from_keywords={"keywords": ["ml", "notes"]},
                discovered_count=2,
                first_discovered_at=now,
                last_discovered_at=now,
                status="pending",
                admin_reviewed_at=None,
                admin_notes=None,
                discovered_from_task_id=None,
                reviewed_by=None,
            )
        )
        await db_session.commit()

        resp = await client.post(
            "/api/admin/communities/approve",
            headers=headers,
            json={"name": "r/approve_me", "tier": "silver"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["approved"] == "r/approve_me"

        stored_pool = (
            await db_session.execute(select(CommunityPool).where(CommunityPool.name == "r/approve_me"))
        ).scalar_one()
        assert stored_pool.tier == "silver"
        assert stored_pool.is_active is True

        stored_pending = (
            await db_session.execute(select(PendingCommunity).where(PendingCommunity.name == "r/approve_me"))
        ).scalar_one()
        assert stored_pending.status == "approved"
        assert stored_pending.reviewed_by is not None
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_reject_marks_pending_rejected(
    client: AsyncClient,
    token_factory,
    db_session: AsyncSession,
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = _override_admin_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        admin_token, _ = await token_factory(email=admin_email)
        headers = {"Authorization": f"Bearer {admin_token}"}

        now = datetime.now(timezone.utc)
        db_session.add(
            PendingCommunity(
                name="r/reject_me",
                discovered_from_keywords={"keywords": ["ml", "badfit"]},
                discovered_count=1,
                first_discovered_at=now,
                last_discovered_at=now,
                status="pending",
                admin_reviewed_at=None,
                admin_notes=None,
                discovered_from_task_id=None,
                reviewed_by=None,
            )
        )
        await db_session.commit()

        resp = await client.post(
            "/api/admin/communities/reject",
            headers=headers,
            json={"name": "r/reject_me", "admin_notes": "not relevant"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["rejected"] == "r/reject_me"

        stored = (
            await db_session.execute(select(PendingCommunity).where(PendingCommunity.name == "r/reject_me"))
        ).scalar_one()
        assert stored.status == "rejected"
        assert stored.admin_notes == "not relevant"
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_disable_community_and_not_found(
    client: AsyncClient,
    token_factory,
    db_session: AsyncSession,
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = _override_admin_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        admin_token, _ = await token_factory(email=admin_email)
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 404 for non-existing
        not_found = await client.delete("/api/admin/communities/r/unknownsub", headers=headers)
        assert not_found.status_code == 404

        # Create then disable
        pool = CommunityPool(
            name="r/to_disable",
            tier="medium",
            categories={"topic": ["general"]},
            description_keywords={"keywords": ["productivity"]},
            daily_posts=10,
            avg_comment_length=20,
            quality_score=0.5,
            priority="low",
            user_feedback_count=0,
            discovered_count=0,
            is_active=True,
        )
        db_session.add(pool)
        await db_session.commit()

        ok = await client.delete("/api/admin/communities/r/to_disable", headers=headers)
        assert ok.status_code == 200
        body = ok.json()
        assert body["code"] == 0
        assert body["data"]["disabled"] == "r/to_disable"

        # Ensure we don't hit identity map cache from earlier insert
        db_session.expire_all()
        stored = (
            await db_session.execute(select(CommunityPool).where(CommunityPool.name == "r/to_disable"))
        ).scalar_one()
        assert stored.is_active is False
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_validation_errors_on_approve_and_reject(
    client: AsyncClient, token_factory
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = _override_admin_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        admin_token, _ = await token_factory(email=admin_email)
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Invalid 'name' (too short/empty) should raise 422
        bad1 = await client.post("/api/admin/communities/approve", headers=headers, json={"name": ""})
        bad2 = await client.post("/api/admin/communities/reject", headers=headers, json={"name": ""})
        assert bad1.status_code == 422
        assert bad2.status_code == 422
    finally:
        app.dependency_overrides.pop(get_settings, None)

