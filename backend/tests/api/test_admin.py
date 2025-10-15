from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.main import app
from app.models.analysis import Analysis
from app.models.task import Task, TaskStatus


async def _override_settings(admin_email: str) -> Settings:
    base = get_settings()
    return base.model_copy(update={"admin_emails_raw": admin_email})


async def test_admin_routes_require_admin(
    client: AsyncClient,
    token_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = await _override_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        class DummyInspect:
            def active(self) -> dict[str, list[int]]:
                return {}

        target = "app.api.routes.admin.celery_app.control.inspect"
        monkeypatch.setattr(target, lambda: DummyInspect())

        token, _ = await token_factory()
        response = await client.get(
            "/api/admin/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_settings, None)


async def test_admin_endpoints_return_expected_payloads(
    client: AsyncClient,
    token_factory,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = await _override_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        admin_token, admin_user_id = await token_factory(email=admin_email)

        class DummyInspect:
            def active(self) -> dict[str, list[int]]:
                return {"worker-a": [1], "worker-b": [2, 3]}

        target = "app.api.routes.admin.celery_app.control.inspect"
        monkeypatch.setattr(target, lambda: DummyInspect())

        baseline_response = await client.get(
            "/api/admin/dashboard/stats",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert baseline_response.status_code == 200
        baseline_metrics = baseline_response.json()["data"]

        now = datetime.now(timezone.utc)
        user_email = f"user-{uuid.uuid4().hex}@example.com"
        _, regular_user_id = await token_factory(email=user_email)

        async def create_task(
            user_id: str,
            start_offset_minutes: int,
            duration_minutes: int,
            cache_hit_rate: float,
        ) -> Task:
            start_at = now - timedelta(minutes=start_offset_minutes)
            completed_at = start_at + timedelta(minutes=duration_minutes)

            task = Task(
                user_id=uuid.UUID(user_id),
                product_description="Admin telemetry task payload",
                status=TaskStatus.COMPLETED,
                started_at=start_at,
                completed_at=completed_at,
            )
            task.created_at = start_at
            db_session.add(task)
            await db_session.flush()

            analysis = Analysis(
                task_id=task.id,
                insights={"pain_points": [], "competitors": [], "opportunities": []},
                sources={
                    "communities": [],
                    "posts_analyzed": 10,
                    "cache_hit_rate": cache_hit_rate,
                },
            )
            db_session.add(analysis)
            return task

        task_admin = await create_task(
            admin_user_id, start_offset_minutes=10, duration_minutes=10, cache_hit_rate=0.75
        )
        task_user_a = await create_task(
            regular_user_id, start_offset_minutes=5, duration_minutes=2, cache_hit_rate=0.5
        )
        task_user_b = await create_task(
            regular_user_id, start_offset_minutes=1, duration_minutes=3, cache_hit_rate=0.9
        )
        await db_session.commit()

        dashboard = await client.get(
            "/api/admin/dashboard/stats",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert dashboard.status_code == 200
        dashboard_body = dashboard.json()
        assert dashboard_body["code"] == 0
        metrics = dashboard_body["data"]
        assert metrics["total_users"] >= baseline_metrics["total_users"] + 1
        assert metrics["total_tasks"] >= baseline_metrics["total_tasks"] + 3
        assert metrics["tasks_today"] >= baseline_metrics["tasks_today"] + 3
        assert metrics["tasks_completed_today"] >= baseline_metrics["tasks_completed_today"] + 3
        assert metrics["active_workers"] == 2
        assert 0 <= metrics["cache_hit_rate"] <= 1
        assert metrics["avg_processing_time"] >= 0

        recent = await client.get(
            "/api/admin/tasks/recent",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert recent.status_code == 200
        recent_body = recent.json()
        assert recent_body["code"] == 0
        recent_items = recent_body["data"]["items"]
        assert len(recent_items) >= 3
        recent_map = {item["task_id"]: item for item in recent_items}
        expected_ids = {str(task_admin.id), str(task_user_a.id), str(task_user_b.id)}
        assert expected_ids.issubset(recent_map.keys())
        assert recent_map[str(task_user_b.id)]["processing_seconds"] == pytest.approx(180.0, rel=1e-3)

        active = await client.get(
            "/api/admin/users/active",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert active.status_code == 200
        active_body = active.json()
        assert active_body["code"] == 0
        active_items = active_body["data"]["items"]
        assert len(active_items) >= 2
        active_map = {item["email"]: item for item in active_items}
        assert user_email in active_map
        assert active_map[user_email]["tasks_last_7_days"] >= 2
        assert admin_email in active_map
        assert active_map[admin_email]["tasks_last_7_days"] >= 1
    finally:
        app.dependency_overrides.pop(get_settings, None)
