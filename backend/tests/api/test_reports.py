from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import jwt
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PACKAGE_ROOT = (PROJECT_ROOT / "backend").resolve()
if str(BACKEND_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_PACKAGE_ROOT))

from app.core.config import get_settings
from app.models.analysis import Analysis
from app.models.report import Report
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.core.security import hash_password


settings = get_settings()

def _issue_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def _create_completed_task(db_session: AsyncSession, with_report: bool = True) -> tuple[User, Task]:
    user = User(email=f"report+{uuid.uuid4().hex}@example.com", password_hash=hash_password("testpass123"))
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
        insights={
            "pain_points": [],
            "competitors": [],
            "opportunities": [],
        },
        sources={
            "communities": [],
            "posts_analyzed": 0,
            "cache_hit_rate": 0.0,
        },
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


async def test_get_report_success(client: AsyncClient, db_session: AsyncSession) -> None:
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


async def test_get_report_permission_denied(client: AsyncClient, db_session: AsyncSession) -> None:
    owner, task = await _create_completed_task(db_session)
    intruder = User(email=f"report-intruder+{uuid.uuid4().hex}@example.com", password_hash=hash_password("testpass123"))
    db_session.add(intruder)
    await db_session.commit()
    await db_session.refresh(intruder)

    token = _issue_token(str(intruder.id))
    response = await client.get(
        f"/api/report/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_get_report_requires_completion(client: AsyncClient, db_session: AsyncSession) -> None:
    user = User(email=f"pending+{uuid.uuid4().hex}@example.com", password_hash=hash_password("testpass123"))
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
