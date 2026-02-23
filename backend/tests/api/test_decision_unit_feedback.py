from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PACKAGE_ROOT = (PROJECT_ROOT / "backend").resolve()
if str(BACKEND_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_PACKAGE_ROOT))

from app.core.config import get_settings
from app.core.security import hash_password

settings = get_settings()


def _issue_token(*, user_id: str, email: str | None = None) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.mark.asyncio
async def test_submit_decision_unit_feedback_persists_event_and_enforces_owner(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    from app.models.insight import Evidence, InsightCard
    from app.models.task import Task, TaskStatus
    from app.models.user import User

    user = User(
        email=f"du-fb-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
    )
    other = User(
        email=f"du-fb-other-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
    )
    db_session.add_all([user, other])
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(other)

    task = Task(
        user_id=user.id,
        product_description="DecisionUnit feedback task",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
        topic_profile_id="shopify_ads_conversion_v1",
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    du = InsightCard(
        task_id=task.id,
        kind="decision_unit",
        signal_type="ops",
        du_schema_version=1,
        du_payload={"claim": "Feedback me", "metrics": {"mentions": 9}},
        title="DecisionUnit feedback",
        summary="DU feedback summary",
        confidence=0.85,
        time_window_days=30,
        subreddits=["r/test"],
    )
    db_session.add(du)
    await db_session.commit()
    await db_session.refresh(du)

    ev_low = Evidence(
        insight_card_id=du.id,
        post_url="https://reddit.com/r/test/comments/low/x/",
        excerpt="Low evidence",
        timestamp=datetime.now(timezone.utc),
        subreddit="r/test",
        score=0.1,
        content_type="post",
        content_id=1,
    )
    ev_high = Evidence(
        insight_card_id=du.id,
        post_url="https://reddit.com/r/test/comments/high/x/",
        excerpt="High evidence",
        timestamp=datetime.now(timezone.utc),
        subreddit="r/test",
        score=0.9,
        content_type="post",
        content_id=2,
    )
    db_session.add_all([ev_low, ev_high])
    await db_session.commit()
    await db_session.refresh(ev_low)
    await db_session.refresh(ev_high)

    token = _issue_token(user_id=str(user.id), email=user.email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        f"/api/decision-units/{du.id}/feedback",
        headers=headers,
        json={"label": "correct", "evidence_id": str(ev_high.id), "note": "looks right"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["decision_unit_id"] == str(du.id)
    assert body["label"] == "correct"
    assert body["evidence_id"] == str(ev_high.id)

    # evidence_id omitted -> server should pick top evidence (ev_high)
    resp2 = await client.post(
        f"/api/decision-units/{du.id}/feedback",
        headers=headers,
        json={"label": "valuable", "note": "worth tracking"},
    )
    assert resp2.status_code == 201
    body2 = resp2.json()
    assert body2["evidence_id"] == str(ev_high.id)

    # Persisted rows exist
    count = int(
        (
            await db_session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM decision_unit_feedback_events
                    WHERE decision_unit_id = :du_id AND user_id = :user_id
                    """
                ),
                {"du_id": du.id, "user_id": user.id},
            )
        ).scalar_one()
        or 0
    )
    assert count >= 2

    # Cross-user access should be blocked (404/403 ok, but not 500)
    other_token = _issue_token(user_id=str(other.id), email=other.email)
    resp_forbidden = await client.post(
        f"/api/decision-units/{du.id}/feedback",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"label": "correct", "evidence_id": str(ev_high.id)},
    )
    assert resp_forbidden.status_code in {403, 404}


@pytest.mark.asyncio
async def test_submit_decision_unit_feedback_rejects_mismatched_evidence(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    from app.models.insight import Evidence, InsightCard
    from app.models.task import Task, TaskStatus
    from app.models.user import User

    user = User(
        email=f"du-fb-mismatch-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("StrongPassw0rd!"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    task = Task(
        user_id=user.id,
        product_description="DecisionUnit feedback mismatch task",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    du_a = InsightCard(
        task_id=task.id,
        kind="decision_unit",
        signal_type="ops",
        du_schema_version=1,
        du_payload={"claim": "A"},
        title="DU A",
        summary="A",
        confidence=0.5,
        time_window_days=30,
        subreddits=["r/test"],
    )
    du_b = InsightCard(
        task_id=task.id,
        kind="decision_unit",
        signal_type="ops",
        du_schema_version=1,
        du_payload={"claim": "B"},
        title="DU B",
        summary="B",
        confidence=0.6,
        time_window_days=30,
        subreddits=["r/test"],
    )
    db_session.add_all([du_a, du_b])
    await db_session.commit()
    await db_session.refresh(du_a)
    await db_session.refresh(du_b)

    ev_b = Evidence(
        insight_card_id=du_b.id,
        post_url="https://reddit.com/r/test/comments/ev_b/x/",
        excerpt="evidence b",
        timestamp=datetime.now(timezone.utc),
        subreddit="r/test",
        score=0.7,
        content_type="post",
        content_id=3,
    )
    db_session.add(ev_b)
    await db_session.commit()
    await db_session.refresh(ev_b)

    token = _issue_token(user_id=str(user.id), email=user.email)
    resp = await client.post(
        f"/api/decision-units/{du_a.id}/feedback",
        headers={"Authorization": f"Bearer {token}"},
        json={"label": "incorrect", "evidence_id": str(ev_b.id), "note": "wrong evidence"},
    )
    assert resp.status_code == 400

