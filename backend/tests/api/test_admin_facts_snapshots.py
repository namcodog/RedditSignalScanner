from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.main import app
from app.models.facts_snapshot import FactsSnapshot
from app.models.task import Task
from app.models.user import User


pytestmark = pytest.mark.asyncio


def _override_admin_settings(admin_email: str) -> Settings:
    base = get_settings()
    return base.model_copy(update={"admin_emails_raw": admin_email})


async def test_admin_can_fetch_latest_facts_snapshot_for_task(
    client: AsyncClient,
    db_session: AsyncSession,
    token_factory,
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = _override_admin_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        token, user_id = await token_factory(email=admin_email)
        headers = {"Authorization": f"Bearer {token}"}

        user = await db_session.get(User, uuid.UUID(user_id))
        assert user is not None

        task = Task(
            user_id=user.id,
            product_description="Admin facts snapshot query test description.",
            mode="market_insight",
        )
        db_session.add(task)
        await db_session.flush()

        snapshot = FactsSnapshot(
            task=task,
            schema_version="2.0",
            v2_package={"schema_version": "2.0", "meta": {"topic": "test"}},
            quality={"passed": True, "tier": "A_full", "flags": [], "metrics": {}},
            passed=True,
            tier="A_full",
        )
        db_session.add(snapshot)
        await db_session.commit()

        resp = await client.get(
            f"/api/admin/facts/tasks/{task.id}/latest",
            headers=headers,
            params={"include_package": True},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["task_id"] == str(task.id)
        assert payload["snapshot_id"] == str(snapshot.id)
        assert payload["tier"] == "A_full"
        assert payload["passed"] is True
        assert payload["v2_package"]["schema_version"] == "2.0"
    finally:
        app.dependency_overrides.pop(get_settings, None)

