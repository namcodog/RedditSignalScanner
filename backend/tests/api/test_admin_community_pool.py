from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.main import app
from app.models.community_pool import CommunityPool
from app.models.discovered_community import DiscoveredCommunity


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
        pending = DiscoveredCommunity(
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
            DiscoveredCommunity(
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
            await db_session.execute(select(DiscoveredCommunity).where(DiscoveredCommunity.name == "r/approve_me"))
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
            DiscoveredCommunity(
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
            await db_session.execute(select(DiscoveredCommunity).where(DiscoveredCommunity.name == "r/reject_me"))
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


@pytest.mark.asyncio
async def test_approve_logs_when_discovered_count_conversion_fails(
    client: AsyncClient,
    token_factory,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import app.api.routes.admin_community_pool as admin_module

    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = _override_admin_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        admin_token, admin_user_id = await token_factory(email=admin_email)
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 启用目标 logger，确保警告会被 caplog 捕获
        original_disabled = admin_module.logger.disabled
        admin_module.logger.disabled = False
        caplog.set_level(logging.WARNING, logger=admin_module.__name__)
        logging.getLogger(admin_module.__name__).propagate = True

        now = datetime.now(timezone.utc)
        db_session.add(
            CommunityPool(
                name="r/logging_case",
                tier="medium",
                categories={"topic": ["automation"]},
                description_keywords={"keywords": ["ops"]},
                daily_posts=10,
                avg_comment_length=40,
                quality_score=0.6,
                priority="medium",
                user_feedback_count=0,
                discovered_count=5,
                is_active=True,
                created_by=uuid.UUID(admin_user_id),
                updated_by=uuid.UUID(admin_user_id),
            )
        )
        db_session.add(
            DiscoveredCommunity(
                name="r/logging_case",
                discovered_from_keywords={"keywords": ["automation"]},
                discovered_count=2,
                first_discovered_at=now,
                last_discovered_at=now,
                status="pending",
            )
        )
        await db_session.commit()

        builtin_safe_int = getattr(admin_module, "safe_int", None)
        assert builtin_safe_int is not None, "safe_int helper must exist in admin_community_pool module"

        flaky_int_calls = {"count": 0}

        def flaky_int(value: object) -> int:
            flaky_int_calls["count"] += 1
            if flaky_int_calls["count"] == 1:
                raise ValueError("boom")
            return builtin_safe_int(value)

        monkeypatch.setattr(admin_module, "safe_int", flaky_int)

        caplog.clear()
        resp = await client.post(
            "/api/admin/communities/approve",
            headers=headers,
            json={"name": "r/logging_case", "tier": "high"},
        )
        assert resp.status_code == 200

        assert flaky_int_calls["count"] >= 2

        messages = [record.getMessage() for record in caplog.records]
        assert any("无法累加" in message for message in messages)
    finally:
        app.dependency_overrides.pop(get_settings, None)
        monkeypatch.setattr(admin_module, "safe_int", builtin_safe_int, raising=False)
        admin_module.logger.disabled = original_disabled
