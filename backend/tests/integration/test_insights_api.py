"""
Integration tests for insights API

基于 speckit-006 User Story 2 (US2) - Task T012
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterator
from uuid import uuid4

import asyncio
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture(scope="module", autouse=True)
def _module_event_loop() -> Iterator[None]:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield
    finally:
        asyncio.set_event_loop(None)
        loop.close()
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.insight import Evidence, InsightCard
from app.models.task import Task, TaskStatus
from app.models.user import MembershipLevel, User


@pytest.mark.asyncio
async def test_get_insights_by_task_id(client: AsyncClient, db_session):
    """测试根据任务 ID 获取洞察卡片列表"""
    # 创建测试用户
    user = User(
        email="test@example.com",
        password_hash=hash_password("test123456"),
        membership_level=MembershipLevel.PRO,
    )
    db_session.add(user)
    await db_session.flush()

    # 创建测试任务
    task = Task(
        user_id=user.id,
        product_description="Test product description",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.flush()

    # 创建测试洞察卡片
    insight_card = InsightCard(
        task_id=task.id,
        title="Test Insight",
        summary="This is a test insight summary",
        confidence=Decimal("0.8500"),
        time_window_days=30,
        subreddits=["r/test1", "r/test2"],
    )
    db_session.add(insight_card)
    await db_session.flush()

    # 创建测试证据
    evidence1 = Evidence(
        insight_card_id=insight_card.id,
        post_url="https://reddit.com/r/test1/comments/abc123",
        excerpt="This is evidence 1",
        timestamp=datetime.now(timezone.utc),
        subreddit="r/test1",
        score=Decimal("0.9000"),
    )
    evidence2 = Evidence(
        insight_card_id=insight_card.id,
        post_url="https://reddit.com/r/test2/comments/def456",
        excerpt="This is evidence 2",
        timestamp=datetime.now(timezone.utc),
        subreddit="r/test2",
        score=Decimal("0.7500"),
    )
    db_session.add_all([evidence1, evidence2])
    await db_session.commit()

    # 生成 JWT token
    from app.core.config import get_settings

    settings = get_settings()
    token, _ = create_access_token(user.id, email=user.email, settings=settings)

    # 调用 API
    response = await client.get(
        "/api/insights",
        params={"task_id": str(task.id)},
        headers={"Authorization": f"Bearer {token}"},
    )

    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1

    # 验证洞察卡片数据
    item = data["items"][0]
    assert item["title"] == "Test Insight"
    assert item["summary"] == "This is a test insight summary"
    assert item["confidence"] == 0.85
    assert item["time_window_days"] == 30
    assert item["subreddits"] == ["r/test1", "r/test2"]
    assert len(item["evidences"]) == 2


@pytest.mark.asyncio
async def test_get_insights_unauthorized(client: AsyncClient, db_session):
    """测试未授权访问返回 401"""
    # 创建测试用户和任务
    user = User(
        email="test@example.com",
        password_hash=hash_password("test123456"),
        membership_level=MembershipLevel.PRO,
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        product_description="Test product description",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()

    # 调用 API（不带 token）
    response = await client.get(
        "/api/insights",
        params={"task_id": str(task.id)},
    )

    # 验证响应
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_insights_forbidden(client: AsyncClient, db_session):
    """测试访问其他用户的任务返回 403"""
    # 创建两个用户
    user1 = User(
        email="user1@example.com",
        password_hash=hash_password("test123456"),
        membership_level=MembershipLevel.PRO,
    )
    user2 = User(
        email="user2@example.com",
        password_hash=hash_password("test123456"),
        membership_level=MembershipLevel.PRO,
    )
    db_session.add_all([user1, user2])
    await db_session.flush()

    # 创建 user1 的任务
    task = Task(
        user_id=user1.id,
        product_description="Test product description",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()

    # 使用 user2 的 token 访问 user1 的任务
    from app.core.config import get_settings

    settings = get_settings()
    token, _ = create_access_token(user2.id, email=user2.email, settings=settings)

    response = await client.get(
        "/api/insights",
        params={"task_id": str(task.id)},
        headers={"Authorization": f"Bearer {token}"},
    )

    # 验证响应
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_insights_task_not_found(client: AsyncClient, db_session):
    """测试任务不存在返回 404"""
    # 创建测试用户
    user = User(
        email="test@example.com",
        password_hash=hash_password("test123456"),
        membership_level=MembershipLevel.PRO,
    )
    db_session.add(user)
    await db_session.commit()

    # 生成 JWT token
    from app.core.config import get_settings

    settings = get_settings()
    token, _ = create_access_token(user.id, email=user.email, settings=settings)

    # 调用 API（使用不存在的 task_id）
    fake_task_id = uuid4()
    response = await client.get(
        "/api/insights",
        params={"task_id": str(fake_task_id)},
        headers={"Authorization": f"Bearer {token}"},
    )

    # 验证响应
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_insights_pagination(client: AsyncClient, db_session):
    """测试分页功能"""
    # 创建测试用户
    user = User(
        email="test@example.com",
        password_hash=hash_password("test123456"),
        membership_level=MembershipLevel.PRO,
    )
    db_session.add(user)
    await db_session.flush()

    # 创建测试任务
    task = Task(
        user_id=user.id,
        product_description="Test product description",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.flush()

    # 创建 15 个洞察卡片
    for i in range(15):
        insight_card = InsightCard(
            task_id=task.id,
            title=f"Test Insight {i}",
            summary=f"This is test insight {i}",
            confidence=Decimal("0.8000"),
            time_window_days=30,
            subreddits=["r/test"],
        )
        db_session.add(insight_card)
    await db_session.commit()

    # 生成 JWT token
    from app.core.config import get_settings

    settings = get_settings()
    token, _ = create_access_token(user.id, email=user.email, settings=settings)

    # 测试第一页（limit=10）
    response = await client.get(
        "/api/insights",
        params={"task_id": str(task.id), "limit": 10, "offset": 0},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 15
    assert len(data["items"]) == 10

    # 测试第二页（limit=10, offset=10）
    response = await client.get(
        "/api/insights",
        params={"task_id": str(task.id), "limit": 10, "offset": 10},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 15
    assert len(data["items"]) == 5


@pytest.mark.asyncio
async def test_get_insight_by_id(client: AsyncClient, db_session):
    """测试根据 ID 获取单个洞察卡片"""
    # 创建测试用户
    user = User(
        email="test@example.com",
        password_hash=hash_password("test123456"),
        membership_level=MembershipLevel.PRO,
    )
    db_session.add(user)
    await db_session.flush()

    # 创建测试任务
    task = Task(
        user_id=user.id,
        product_description="Test product description",
        status=TaskStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.flush()

    # 创建测试洞察卡片
    insight_card = InsightCard(
        task_id=task.id,
        title="Test Insight",
        summary="This is a test insight summary",
        confidence=Decimal("0.8500"),
        time_window_days=30,
        subreddits=["r/test1", "r/test2"],
    )
    db_session.add(insight_card)
    await db_session.commit()

    # 生成 JWT token
    from app.core.config import get_settings

    settings = get_settings()
    token, _ = create_access_token(user.id, email=user.email, settings=settings)

    # 调用 API
    response = await client.get(
        f"/api/insights/{insight_card.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(insight_card.id)
    assert data["title"] == "Test Insight"
    assert data["confidence"] == 0.85
