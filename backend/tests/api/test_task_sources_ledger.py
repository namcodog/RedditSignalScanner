import uuid
from datetime import datetime, timezone
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Analysis, Task, TaskStatus


@pytest.mark.asyncio
async def test_task_sources_ledger_returns_sources_for_owner(
    client: AsyncClient,
    db_session: AsyncSession,
    token_factory,
) -> None:
    token, user_id = await token_factory()
    user_uuid = UUID(user_id)
    task_id = uuid.uuid4()

    task = Task(
        id=task_id,
        user_id=user_uuid,
        product_description="Test product description for sources ledger.",
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
            "comments_analyzed": 7,
            "cache_hit_rate": 0.5,
            "analysis_duration_seconds": 1,
            "reddit_api_calls": 0,
            "data_source": "synthetic",
            "facts_v2_quality": {"tier": "B_trimmed", "flags": ["pains_low"]},
            "report_tier": "B_trimmed",
        },
    )
    db_session.add(analysis)
    await db_session.commit()

    resp = await client.get(
        f"/api/tasks/{task_id}/sources",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["task_id"] == str(task_id)
    assert payload["status"] == "completed"
    assert payload["sources"]["report_tier"] == "B_trimmed"
    assert payload["sources"]["posts_analyzed"] == 42


@pytest.mark.asyncio
async def test_task_sources_ledger_forbidden_for_other_user(
    client: AsyncClient,
    db_session: AsyncSession,
    token_factory,
) -> None:
    owner_token, owner_id = await token_factory()
    intruder_token, _intruder_id = await token_factory()

    owner_uuid = UUID(owner_id)
    task_id = uuid.uuid4()

    task = Task(
        id=task_id,
        user_id=owner_uuid,
        product_description="Forbidden sources ledger test.",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    db_session.add(
        Analysis(
            task_id=task_id,
            insights={"pain_points": [], "competitors": [], "opportunities": []},
            sources={
                "communities": ["r/shopify"],
                "posts_analyzed": 1,
                "comments_analyzed": 0,
                "cache_hit_rate": 1.0,
                "analysis_duration_seconds": 1,
                "reddit_api_calls": 0,
                "data_source": "synthetic",
                "facts_v2_quality": {"tier": "C_scouting", "flags": ["pains_low"]},
                "report_tier": "C_scouting",
            },
        )
    )
    await db_session.commit()

    resp = await client.get(
        f"/api/tasks/{task_id}/sources",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert resp.status_code == 403
