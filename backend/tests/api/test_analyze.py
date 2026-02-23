from __future__ import annotations

import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PACKAGE_ROOT = (PROJECT_ROOT / "backend").resolve()
if str(BACKEND_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_PACKAGE_ROOT))

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.models.analysis import Analysis
from app.models.example_library import ExampleLibrary
from app.models.report import Report
from app.models.task import Task
from app.models.user import User
from app.core.security import hash_password

settings = get_settings()


@pytest.fixture(autouse=True)
def _fast_execute_analysis_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    大白话：本文件里的测试只关心“创建 task 的入库字段对不对”，不关心真正跑分析。
    所以把分析管道换成 no-op，避免后台任务占着 DB 锁，导致 teardown 的 TRUNCATE 超时。
    """
    from app.api.v1.endpoints import analyze as analyze_module

    async def _noop_execute_analysis_pipeline(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(analyze_module, "execute_analysis_pipeline", _noop_execute_analysis_pipeline)


def _issue_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _parse_iso(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


async def test_create_analysis_task(client: AsyncClient, db_session: AsyncSession) -> None:
    unique_email = f"tester+{uuid.uuid4().hex}@example.com"
    user = User(email=unique_email, password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = _issue_token(str(user.id))
    payload = {"product_description": "AI helper that summarises product feedback from Reddit."}

    response = await client.post(
        "/api/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()

    assert "task_id" in data
    assert data["status"] == "pending"
    assert response.headers["Location"] == data["sse_endpoint"]

    created_at = _parse_iso(data["created_at"])
    estimated = _parse_iso(data["estimated_completion"])
    delta = abs((estimated - created_at) - timedelta(minutes=settings.estimated_processing_minutes))
    assert delta < timedelta(seconds=1)

    async with SessionFactory() as verify_session:
        task = await verify_session.get(Task, uuid.UUID(data["task_id"]))
        assert task is not None
        assert task.product_description == payload["product_description"].strip()
        assert task.mode == "market_insight"
        assert task.topic_profile_id is None
        # 默认规则：topic_profile_id 不存在 -> lab（允许后续显式覆盖）
        assert task.audit_level == "lab"


async def test_create_analysis_task_accepts_example_id(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EXAMPLE_REPORT_DELAY_MIN_SECONDS", "0")
    monkeypatch.setenv("EXAMPLE_REPORT_DELAY_MAX_SECONDS", "0")

    unique_email = f"tester+{uuid.uuid4().hex}@example.com"
    user = User(email=unique_email, password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    example = ExampleLibrary(
        title="跨境电商",
        prompt="跨境电商卖家多平台回款与手续费管理工具，覆盖 Amazon/Etsy/Shopify。",
        tags=["跨境电商"],
        analysis_insights={"pain_points": [], "competitors": [], "opportunities": []},
        analysis_sources={
            "report_structured": {
                "decision_cards": [],
                "market_health": {},
                "battlefields": [],
                "pain_points": [],
                "drivers": [],
                "opportunities": [],
            }
        },
        report_html="<h1>Example Report</h1>",
        report_template_version="1.0",
        is_active=True,
    )
    db_session.add(example)
    await db_session.commit()
    await db_session.refresh(example)

    token = _issue_token(str(user.id))
    payload = {
        "product_description": "placeholder description that should be overridden",
        "example_id": str(example.id),
    }

    response = await client.post(
        "/api/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()

    created_at = _parse_iso(data["created_at"])
    estimated = _parse_iso(data["estimated_completion"])
    assert abs((estimated - created_at).total_seconds()) < 1

    async with SessionFactory() as verify_session:
        task = await verify_session.get(Task, uuid.UUID(data["task_id"]))
        assert task is not None
        assert task.product_description == example.prompt
        assert task.status.value == "completed"

        analysis = await verify_session.scalar(
            select(Analysis).where(Analysis.task_id == task.id)
        )
        assert analysis is not None

        report = await verify_session.scalar(
            select(Report).where(Report.analysis_id == analysis.id)
        )
        assert report is not None


async def test_create_analysis_task_v1_alias(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    unique_email = f"tester+{uuid.uuid4().hex}@example.com"
    user = User(email=unique_email, password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = _issue_token(str(user.id))
    payload = {"product_description": "Tooling that helps small teams track operations."}

    response = await client.post(
        "/api/v1/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()

    async with SessionFactory() as verify_session:
        task = await verify_session.get(Task, uuid.UUID(data["task_id"]))
        assert task is not None


async def test_create_analysis_task_accepts_operations_mode(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    unique_email = f"tester+{uuid.uuid4().hex}@example.com"
    user = User(email=unique_email, password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = _issue_token(str(user.id))
    payload = {
        "product_description": "Tooling that helps Amazon sellers improve logistics and operations.",
        "mode": "operations",
    }

    response = await client.post(
        "/api/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()

    async with SessionFactory() as verify_session:
        task = await verify_session.get(Task, uuid.UUID(data["task_id"]))
        assert task is not None
        assert task.mode == "operations"


async def test_create_analysis_task_rejects_invalid_mode(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    unique_email = f"tester+{uuid.uuid4().hex}@example.com"
    user = User(email=unique_email, password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = _issue_token(str(user.id))
    payload = {
        "product_description": "AI helper that summarises product feedback from Reddit.",
        "mode": "auto",
    }

    response = await client.post(
        "/api/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


async def test_create_analysis_task_accepts_topic_profile_id(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    unique_email = f"tester+{uuid.uuid4().hex}@example.com"
    user = User(email=unique_email, password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = _issue_token(str(user.id))
    payload = {
        "product_description": "Optimize Shopify ads conversion funnels with better ROAS and attribution.",
        "topic_profile_id": "shopify_ads_conversion_v1",
    }

    response = await client.post(
        "/api/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()

    async with SessionFactory() as verify_session:
        task = await verify_session.get(Task, uuid.UUID(data["task_id"]))
        assert task is not None
        assert task.topic_profile_id == "shopify_ads_conversion_v1"
        # 默认规则：topic_profile_id 存在 -> gold
        assert task.audit_level == "gold"
        # 未显式传 mode 时，按 TopicProfile 规则自动选择
        assert task.mode == "operations"


async def test_create_analysis_task_accepts_explicit_audit_level_override(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    unique_email = f"tester+{uuid.uuid4().hex}@example.com"
    user = User(email=unique_email, password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = _issue_token(str(user.id))
    payload = {
        "product_description": "Quick exploratory run that should not store full audits.",
        "audit_level": "noise",
    }

    response = await client.post(
        "/api/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()

    async with SessionFactory() as verify_session:
        task = await verify_session.get(Task, uuid.UUID(data["task_id"]))
        assert task is not None
    assert task.audit_level == "noise"


async def test_create_analysis_task_explicit_mode_overrides_topic_profile(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    unique_email = f"tester+{uuid.uuid4().hex}@example.com"
    user = User(email=unique_email, password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = _issue_token(str(user.id))
    payload = {
        "product_description": "Optimize Shopify ads conversion funnels with better ROAS.",
        "topic_profile_id": "shopify_ads_conversion_v1",
        "mode": "market_insight",
    }

    response = await client.post(
        "/api/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()

    async with SessionFactory() as verify_session:
        task = await verify_session.get(Task, uuid.UUID(data["task_id"]))
        assert task is not None
        assert task.topic_profile_id == "shopify_ads_conversion_v1"
        # 显式 mode 优先，不被 TopicProfile 覆盖
        assert task.mode == "market_insight"


async def test_create_analysis_task_rejects_invalid_audit_level(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    unique_email = f"tester+{uuid.uuid4().hex}@example.com"
    user = User(email=unique_email, password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = _issue_token(str(user.id))
    payload = {
        "product_description": "AI helper that summarises product feedback from Reddit.",
        "audit_level": "random",
    }

    response = await client.post(
        "/api/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_create_analysis_task_rejects_unknown_topic_profile_id(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    unique_email = f"tester+{uuid.uuid4().hex}@example.com"
    user = User(email=unique_email, password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = _issue_token(str(user.id))
    payload = {
        "product_description": "Optimize Shopify ads conversion funnels with better ROAS and attribution.",
        "topic_profile_id": "does_not_exist",
    }

    response = await client.post(
        "/api/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_create_analysis_task_requires_token(client: AsyncClient) -> None:
    response = await client.post(
        "/api/analyze",
        json={"product_description": "A valid product description text."},
    )
    assert response.status_code == 401


async def test_create_analysis_task_returns_503_when_celery_broker_down(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
) -> None:
    """
    大白话：当你明确要求走 Celery（ENABLE_CELERY_DISPATCH=1）但队列挂了，
    API 不能假装成功，也不能 500；应该明确返回 503。
    """
    from app.core.config import get_settings

    # 强制开启 Celery 派发（否则测试环境默认会走 inline）
    monkeypatch.setenv("ENABLE_CELERY_DISPATCH", "1")
    get_settings.cache_clear()
    current_settings = get_settings()

    unique_email = f"tester+{uuid.uuid4().hex}@example.com"
    user = User(email=unique_email, password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = jwt.encode(
        {
            "sub": str(user.id),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
        },
        current_settings.jwt_secret,
        algorithm=current_settings.jwt_algorithm,
    )

    # 模拟 broker down：send_task 直接抛异常
    from app.api.v1.endpoints import analyze as analyze_module

    def _raise_send_task(*_args, **_kwargs):
        raise RuntimeError("broker down (simulated)")

    monkeypatch.setattr(analyze_module.celery_app, "send_task", _raise_send_task)

    payload = {"product_description": "Broker down smoke test (should return 503)."}
    response = await client.post(
        "/api/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503

    # 不允许留下“孤儿 task”（否则用户重试会越积越多）
    async with SessionFactory() as verify_session:
        result = await verify_session.execute(
            select(Task.id).where(Task.user_id == user.id)
        )
        assert result.first() is None


async def test_create_analysis_task_returns_503_fast_when_send_task_hangs(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
) -> None:
    """
    大白话：broker/网络抖的时候，send_task 不能把 API 卡死。
    这里模拟 send_task 卡住，要求 API 在超时内快速返回 503。
    """
    from app.core.config import get_settings

    monkeypatch.setenv("ENABLE_CELERY_DISPATCH", "1")
    monkeypatch.setenv("CELERY_DISPATCH_TIMEOUT_SECONDS", "0.05")
    get_settings.cache_clear()
    current_settings = get_settings()

    unique_email = f"tester+{uuid.uuid4().hex}@example.com"
    user = User(email=unique_email, password_hash=hash_password("testpass123"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = jwt.encode(
        {
            "sub": str(user.id),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
        },
        current_settings.jwt_secret,
        algorithm=current_settings.jwt_algorithm,
    )

    from app.api.v1.endpoints import analyze as analyze_module

    def _slow_send_task(*_args, **_kwargs):
        time.sleep(0.3)
        raise RuntimeError("send_task hang simulated")

    monkeypatch.setattr(analyze_module.celery_app, "send_task", _slow_send_task)

    started = time.perf_counter()
    response = await client.post(
        "/api/analyze",
        json={"product_description": "Send task hang test (should return 503 fast)."},
        headers={"Authorization": f"Bearer {token}"},
    )
    elapsed = time.perf_counter() - started

    assert response.status_code == 503
    assert elapsed < 1.0

    async with SessionFactory() as verify_session:
        result = await verify_session.execute(
            select(Task.id).where(Task.user_id == user.id)
        )
        assert result.first() is None
