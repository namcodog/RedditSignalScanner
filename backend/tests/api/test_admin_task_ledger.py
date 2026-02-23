import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Analysis, Task, TaskStatus, User
from app.models.facts_snapshot import FactsSnapshot


@pytest.mark.asyncio
async def test_admin_task_ledger_returns_sources_and_facts_snapshot(
    client: AsyncClient,
    db_session: AsyncSession,
    token_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_email = f"admin-ledger-{uuid.uuid4().hex}@example.com"
    monkeypatch.setenv("ADMIN_EMAILS", admin_email)
    token, user_id = await token_factory(email=admin_email)

    user_uuid = uuid.UUID(user_id)
    task_id = uuid.uuid4()

    # Ensure user exists (token_factory creates it via /api/auth/register).
    user = await db_session.get(User, user_uuid)
    assert user is not None

    task = Task(
        id=task_id,
        user_id=user_uuid,
        product_description="Test product description for admin ledger.",
        status=TaskStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)

    analysis = Analysis(
        task_id=task_id,
        insights={"pain_points": [], "competitors": [], "opportunities": []},
        sources={
            "communities": ["r/shopify"],
            "posts_analyzed": 42,
            "cache_hit_rate": 0.5,
            "analysis_duration_seconds": 1,
            "reddit_api_calls": 0,
            "data_source": "synthetic",
            "facts_v2_quality": {"tier": "B_trimmed", "flags": ["pains_low"]},
            "report_tier": "B_trimmed",
        },
    )
    db_session.add(analysis)

    snapshot = FactsSnapshot(
        task_id=task_id,
        schema_version="2.0",
        v2_package={"schema_version": "2.0", "data_lineage": {"source_range": {"posts": 42}}},
        quality={"tier": "B_trimmed", "flags": ["pains_low"], "passed": True},
        passed=True,
        tier="B_trimmed",
        audit_level="lab",
        status="ok",
        validator_level="info",
        retention_days=30,
    )
    db_session.add(snapshot)
    await db_session.commit()

    resp = await client.get(
        f"/api/admin/tasks/{task_id}/ledger",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["task"]["id"] == str(task_id)
    assert payload["task"]["status"] == "completed"
    assert payload["analysis"]["sources"]["posts_analyzed"] == 42
    assert payload["facts_snapshot"]["tier"] == "B_trimmed"
