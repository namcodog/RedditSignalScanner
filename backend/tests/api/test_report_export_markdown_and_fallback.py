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


async def _create_completed_task(db_session: AsyncSession) -> tuple[User, Task]:
    user = User(
        email=f"export+{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("testpass123"),
        membership_level=MembershipLevel.PRO,
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
        insights={"pain_points": [], "competitors": [], "opportunities": []},
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
async def test_download_report_markdown_success(client: AsyncClient, db_session: AsyncSession) -> None:
    user, task = await _create_completed_task(db_session)
    token = _issue_token(str(user.id))
    resp = await client.get(
        f"/api/report/{task.id}/download",
        params={"format": "md"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    content = resp.content.decode("utf-8")
    assert content.startswith("# Reddit Signal Scanner 报告")


@pytest.mark.asyncio
async def test_download_report_pdf_fallback_to_json(client: AsyncClient, db_session: AsyncSession) -> None:
    user, task = await _create_completed_task(db_session)
    token = _issue_token(str(user.id))
    resp = await client.get(
        f"/api/report/{task.id}/download",
        params={"format": "pdf"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # 在未安装 WeasyPrint 时，会降级为 JSON
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.headers.get("X-Export-Fallback") == "json"
    data = json.loads(resp.content.decode("utf-8"))
    assert data["task_id"] == str(task.id)

