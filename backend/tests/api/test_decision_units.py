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

settings = get_settings()


def _issue_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.mark.asyncio
async def test_list_decision_units_scopes_to_user_and_supports_task_filter(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    from app.models.insight import InsightCard
    from app.models.task import Task, TaskStatus
    from app.models.user import User

    user_a = User(
        email=f"du-a-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
    )
    user_b = User(
        email=f"du-b-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
    )
    db_session.add_all([user_a, user_b])
    await db_session.commit()
    await db_session.refresh(user_a)
    await db_session.refresh(user_b)

    task_a1 = Task(
        user_id=user_a.id,
        product_description="DecisionUnit list task A1",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    task_a2 = Task(
        user_id=user_a.id,
        product_description="DecisionUnit list task A2",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    task_b1 = Task(
        user_id=user_b.id,
        product_description="DecisionUnit list task B1",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add_all([task_a1, task_a2, task_b1])
    await db_session.commit()
    await db_session.refresh(task_a1)
    await db_session.refresh(task_a2)
    await db_session.refresh(task_b1)

    du_a1 = InsightCard(
        task_id=task_a1.id,
        kind="decision_unit",
        signal_type="ops",
        du_schema_version=1,
        du_payload={"claim": "A1", "metrics": {"mentions": 1}},
        title="Shared title",
        summary="DU A1 summary",
        confidence=0.8,
        time_window_days=30,
        subreddits=["r/test"],
    )
    du_a2 = InsightCard(
        task_id=task_a2.id,
        kind="decision_unit",
        signal_type="ops",
        du_schema_version=1,
        du_payload={"claim": "A2", "metrics": {"mentions": 2}},
        title="Shared title",
        summary="DU A2 summary",
        confidence=0.7,
        time_window_days=30,
        subreddits=["r/test"],
    )
    du_b1 = InsightCard(
        task_id=task_b1.id,
        kind="decision_unit",
        signal_type="ops",
        du_schema_version=1,
        du_payload={"claim": "B1", "metrics": {"mentions": 3}},
        title="Shared title",
        summary="DU B1 summary",
        confidence=0.9,
        time_window_days=30,
        subreddits=["r/test"],
    )
    db_session.add_all([du_a1, du_a2, du_b1])
    await db_session.commit()

    token_a = _issue_token(str(user_a.id))

    resp_all = await client.get(
        "/api/decision-units",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_all.status_code == 200
    payload_all = resp_all.json()
    assert payload_all["total"] == 2
    assert {item["du_payload"]["claim"] for item in payload_all["items"]} == {"A1", "A2"}

    resp_task = await client.get(
        "/api/decision-units",
        params={"task_id": str(task_a1.id)},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_task.status_code == 200
    payload_task = resp_task.json()
    assert payload_task["total"] == 1
    assert payload_task["items"][0]["task_id"] == str(task_a1.id)
    assert payload_task["items"][0]["du_payload"]["claim"] == "A1"


@pytest.mark.asyncio
async def test_get_decision_unit_detail_includes_evidence_and_enforces_owner(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    from app.models.insight import Evidence, InsightCard
    from app.models.task import Task, TaskStatus
    from app.models.user import User

    user = User(
        email=f"du-detail-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
    )
    other = User(
        email=f"du-other-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
    )
    db_session.add_all([user, other])
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(other)

    task = Task(
        user_id=user.id,
        product_description="DecisionUnit detail task",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    du = InsightCard(
        task_id=task.id,
        kind="decision_unit",
        signal_type="ops",
        du_schema_version=1,
        du_payload={"claim": "Detail", "metrics": {"mentions": 9}},
        title="DecisionUnit detail",
        summary="DU detail summary",
        confidence=0.85,
        time_window_days=30,
        subreddits=["r/test"],
    )
    db_session.add(du)
    await db_session.commit()
    await db_session.refresh(du)

    evidence = Evidence(
        insight_card_id=du.id,
        post_url="https://reddit.com/r/test/comments/abc123/x/",
        excerpt="This is evidence",
        timestamp=datetime.now(timezone.utc),
        subreddit="r/test",
        score=0.9,
        content_type="post",
        content_id=123,
    )
    db_session.add(evidence)
    await db_session.commit()

    token = _issue_token(str(user.id))
    resp = await client.get(
        f"/api/decision-units/{du.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["id"] == str(du.id)
    assert payload["du_payload"]["claim"] == "Detail"
    assert payload["evidence"]
    assert payload["evidence"][0]["content_type"] == "post"
    assert payload["evidence"][0]["content_id"] == 123

    other_token = _issue_token(str(other.id))
    resp_forbidden = await client.get(
        f"/api/decision-units/{du.id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp_forbidden.status_code in {403, 404}

