from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PACKAGE_ROOT = (PROJECT_ROOT / "backend").resolve()
if str(BACKEND_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_PACKAGE_ROOT))

from app.api.routes.reports import REPORT_RATE_LIMITER
from app.core.config import get_settings
from app.core.security import hash_password
from app.models.analysis import Analysis
from app.models.report import Report
from app.models.task import Task, TaskStatus
from app.models.user import MembershipLevel, User

settings = get_settings()


def _issue_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def _create_completed_task(
    db_session: AsyncSession,
    *,
    with_report: bool = True,
    insights_payload: dict | None = None,
    sources_payload: dict | None = None,
    membership_level: MembershipLevel = MembershipLevel.PRO,
) -> tuple[User, Task]:
    user = User(
        email=f"report+{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("testpass123"),
        membership_level=membership_level,
    )
    db_session.add(user)
    await db_session.flush()
    task = Task(
        user_id=user.id,
        product_description="Generate report",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.flush()

    analysis = Analysis(
        task_id=task.id,
        insights=insights_payload
        or {
            "pain_points": [],
            "competitors": [],
            "opportunities": [],
        },
        sources=sources_payload
        or {
            "communities": [],
            "posts_analyzed": 0,
            "cache_hit_rate": 0.0,
        },
        analysis_version=1,
    )
    db_session.add(analysis)
    await db_session.flush()

    if with_report:
        report = Report(
            analysis_id=analysis.id,
            html_content="<html>report</html>",
            template_version="1.0",
            generated_at=datetime.now(timezone.utc),
        )
        db_session.add(report)

    await db_session.commit()
    await db_session.refresh(task)

    return user, task


async def test_get_report_success(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user, task = await _create_completed_task(db_session)
    token = _issue_token(str(user.id))

    response = await client.get(
        f"/api/report/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == str(task.id)
    assert data["status"] == TaskStatus.COMPLETED.value
    assert "generated_at" in data

    summary = data["report"]["executive_summary"]
    assert summary["total_communities"] == 0
    assert summary["key_insights"] == 0
    assert summary["top_opportunity"] == ""

    assert isinstance(data["report"]["pain_points"], list)
    assert isinstance(data["report"]["competitors"], list)
    assert isinstance(data["report"]["opportunities"], list)
    assert isinstance(data["report"].get("action_items"), list)
    entity_summary = data["report"].get("entity_summary")
    assert isinstance(entity_summary, dict)
    for category in ("brands", "features", "pain_points"):
        assert category in entity_summary
        assert isinstance(entity_summary[category], list)
    assert data["report_html"].startswith("<html>")

    metadata = data["metadata"]
    assert metadata["analysis_version"] == "1.0"
    assert metadata["cache_hit_rate"] == 0.0
    assert metadata["total_mentions"] == 0

    overview = data["overview"]
    assert "sentiment" in overview
    assert "top_communities" in overview

    pain_points = data["report"]["pain_points"]
    if pain_points:
        assert isinstance(pain_points[0].get("example_posts"), list)


async def test_get_report_permission_denied(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, task = await _create_completed_task(db_session)
    intruder = User(
        email=f"report-intruder+{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("testpass123"),
    )
    db_session.add(intruder)
    await db_session.commit()
    await db_session.refresh(intruder)

    token = _issue_token(str(intruder.id))
    response = await client.get(
        f"/api/report/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_get_report_requires_paid_plan(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user, task = await _create_completed_task(
        db_session, membership_level=MembershipLevel.FREE
    )
    token = _issue_token(str(user.id))

    response = await client.get(
        f"/api/report/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_get_report_requires_completion(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = User(
        email=f"pending+{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("testpass123"),
    )
    db_session.add(user)
    await db_session.flush()
    task = Task(user_id=user.id, product_description="Pending report")
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    token = _issue_token(str(user.id))
    response = await client.get(
        f"/api/report/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409


async def test_get_report_returns_structured_stats(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user, task = await _create_completed_task(db_session)
    token = _issue_token(str(user.id))

    response = await client.get(
        f"/api/report/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    stats = payload.get("stats")
    assert stats is not None
    assert stats["total_mentions"] >= 0
    assert {"positive_mentions", "negative_mentions", "neutral_mentions"}.issubset(
        stats.keys()
    )


@pytest.mark.asyncio
async def test_get_report_enforces_rate_limit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user, task = await _create_completed_task(db_session)
    token = _issue_token(str(user.id))

    limit = 2
    original_limit = getattr(settings, "report_rate_limit_per_minute", None)
    original_window = getattr(settings, "report_rate_limit_window_seconds", None)
    setattr(settings, "report_rate_limit_per_minute", limit)
    REPORT_RATE_LIMITER.configure(
        max_requests=limit,
        window_seconds=settings.report_rate_limit_window_seconds,
    )

    try:
        for _ in range(limit):
            ok_response = await client.get(
                f"/api/report/{task.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert ok_response.status_code == 200

        throttled = await client.get(
            f"/api/report/{task.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert throttled.status_code == 429
        body = throttled.json()
        assert "detail" in body
    finally:
        if original_limit is not None:
            setattr(settings, "report_rate_limit_per_minute", original_limit)
        if original_window is not None:
            setattr(settings, "report_rate_limit_window_seconds", original_window)
        REPORT_RATE_LIMITER.configure(
            max_requests=settings.report_rate_limit_per_minute,
            window_seconds=settings.report_rate_limit_window_seconds,
        )


async def test_download_report_json_success(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user, task = await _create_completed_task(db_session)
    token = _issue_token(str(user.id))

    response = await client.get(
        f"/api/report/{task.id}/download",
        params={"format": "json"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["content-disposition"].endswith('.json"')

    payload = json.loads(response.content.decode("utf-8"))
    assert payload["task_id"] == str(task.id)
    assert payload["status"] == TaskStatus.COMPLETED.value


async def test_download_report_requires_authentication(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, task = await _create_completed_task(db_session)

    response = await client.get(f"/api/report/{task.id}/download")

    assert response.status_code == 401


async def test_download_report_not_found_when_missing_artifact(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user, task = await _create_completed_task(db_session, with_report=False)
    token = _issue_token(str(user.id))

    response = await client.get(
        f"/api/report/{task.id}/download",
        params={"format": "json"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


@pytest.mark.skip(
    reason="Database constraints now prevent invalid insights from being inserted. This test is no longer valid as the validation happens at the database level."
)
async def test_get_report_invalid_insights_returns_server_error(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # 缺少 sentiment_score 字段将触发服务层验证失败
    # NOTE: This test is now skipped because database constraints prevent
    # invalid insights from being inserted in the first place.
    # The validation now happens at the database level via check constraints.
    insights_payload = {
        "pain_points": [
            {
                "description": "缺少关键字段",
                "frequency": 10,
            }
        ],
        "competitors": [],
        "opportunities": [],
    }

    user, task = await _create_completed_task(
        db_session, insights_payload=insights_payload
    )
    token = _issue_token(str(user.id))

    response = await client.get(
        f"/api/report/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 500
    body = response.json()
    assert body["detail"].startswith("Failed to validate analysis payload")
