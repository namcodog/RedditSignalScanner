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
from app.models.insight import InsightCard
from app.models.task import Task, TaskStatus
from app.models.user import User

settings = get_settings()


def _issue_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.mark.asyncio
async def test_get_insights_filters_by_min_confidence(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # Arrange: create user and task
    user = User(
        email=f"test-insights-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        product_description="Benchmark automation insights",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    # Seed three cards with varying confidence
    cards = [
        InsightCard(
            task_id=task.id,
            title="Low confidence insight",
            summary="Needs validation",
            confidence=0.2,
            time_window_days=30,
            subreddits=["r/test"],
        ),
        InsightCard(
            task_id=task.id,
            title="Medium confidence insight",
            summary="Looks promising",
            confidence=0.55,
            time_window_days=30,
            subreddits=["r/test"],
        ),
        InsightCard(
            task_id=task.id,
            title="High confidence insight",
            summary="Ready for action",
            confidence=0.85,
            time_window_days=30,
            subreddits=["r/test"],
        ),
    ]
    db_session.add_all(cards)
    await db_session.commit()

    token = _issue_token(str(user.id))

    # Act: fetch with a confidence filter that should return only the highest card
    response = await client.get(
        "/api/insights",
        params={"min_confidence": 0.6},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Assert
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["confidence"] >= 0.6
    assert payload["items"][0]["title"] == "High confidence insight"

    # Act again without filter – should return all cards
    response_all = await client.get(
        "/api/insights",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response_all.status_code == 200
    all_payload = response_all.json()
    assert all_payload["total"] == 3
    assert len(all_payload["items"]) == 3


@pytest.mark.asyncio
async def test_get_insights_filters_by_subreddit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """当请求附带 subreddit 参数时，仅返回对应子版块的洞察。"""

    user = User(
        email=f"test-subreddit-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        product_description="Filter insights by subreddit",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    matching = InsightCard(
        task_id=task.id,
        title="Match",
        summary="Contains target subreddit",
        confidence=0.9,
        time_window_days=7,
        subreddits=["r/productivity", "r/startups"],
    )
    non_matching = InsightCard(
        task_id=task.id,
        title="Other",
        summary="Different subreddit",
        confidence=0.8,
        time_window_days=7,
        subreddits=["r/indiehackers"],
    )
    db_session.add_all([matching, non_matching])
    await db_session.commit()

    token = _issue_token(str(user.id))

    response = await client.get(
        "/api/insights",
        params={"task_id": str(task.id), "subreddit": "r/startups"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == str(matching.id)
    assert "r/startups" in payload["items"][0]["subreddits"]

    # 不传参数应返回全部记录
    response_all = await client.get(
        "/api/insights",
        params={"task_id": str(task.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response_all.status_code == 200
    all_payload = response_all.json()
    assert all_payload["total"] == 2
    assert {item["id"] for item in all_payload["items"]} == {
        str(matching.id),
        str(non_matching.id),
    }
