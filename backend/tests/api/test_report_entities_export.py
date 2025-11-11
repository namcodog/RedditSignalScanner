from __future__ import annotations

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
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def _create_task_with_insights(db_session: AsyncSession) -> tuple[User, Task]:
    user = User(
        email=f"entities+{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("testpass123"),
        membership_level=MembershipLevel.PRO,
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        product_description="Entity export test",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.flush()

    insights_payload = {
        "pain_points": [
            {
                "description": "Notification overload on Slack and Discord",
                "frequency": 3,
                "sentiment_score": -0.4,
                "severity": "medium",
                "example_posts": [],
                "user_examples": [],
            }
        ],
        "competitors": [
            {"name": "Notion", "mentions": 2, "sentiment": "neutral", "strengths": [], "weaknesses": []},
        ],
        "opportunities": [
            {
                "description": "Build calendar automation and summarization",
                "relevance_score": 0.8,
                "potential_users": "~200",
                "key_insights": [],
                "source_examples": [],
            }
        ],
    }
    analysis = Analysis(
        task_id=task.id,
        insights=insights_payload,
        sources={"communities": [], "posts_analyzed": 0, "cache_hit_rate": 0.0},
        analysis_version=1,
    )
    db_session.add(analysis)
    await db_session.flush()

    report = Report(
        analysis_id=analysis.id,
        html_content="<html>report</html>",
        template_version="1.0",
        generated_at=datetime.now(timezone.utc),
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(task)
    await db_session.refresh(user)

    return user, task


@pytest.mark.asyncio
async def test_export_entities_json(client: AsyncClient, db_session: AsyncSession) -> None:
    user, task = await _create_task_with_insights(db_session)
    token = _issue_token(str(user.id))

    resp = await client.get(
        f"/api/report/{task.id}/entities",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["task_id"] == str(task.id)
    items = payload.get("items") or []
    assert isinstance(items, list)
    # Should contain at least one from default.yml (Slack/Discord/Notion/calendar/summarization)
    names = {it.get("name") for it in items}
    assert any(name in names for name in ("Slack", "Discord", "Notion", "calendar", "summarization"))


@pytest.mark.asyncio
async def test_download_entities_csv(client: AsyncClient, db_session: AsyncSession) -> None:
    user, task = await _create_task_with_insights(db_session)
    token = _issue_token(str(user.id))

    resp = await client.get(
        f"/api/report/{task.id}/entities/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    content = resp.content.decode("utf-8")
    # Header row should exist
    assert "name,category,mentions" in content.replace(" ", "")
