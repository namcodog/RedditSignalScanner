"""最小化性能测试 - 用于诊断"""
from __future__ import annotations

import asyncio
import pytest
from httpx import AsyncClient

from .utils import install_fast_analysis, wait_for_task_completion


@pytest.mark.asyncio
async def test_single_task_creation(
    client: AsyncClient,
    token_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """测试单个任务创建 - 最小化版本"""

    cache_stats: dict[str, int] = {}
    install_fast_analysis(monkeypatch, cache_stats=cache_stats)

    # 创建一个用户
    print("📝 Creating user...")
    token, user_id = await token_factory(password="TestUser123!", email="test@example.com")
    print(f"✅ User created: {user_id}")

    # 提交一个任务
    print("📝 Submitting task...")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/api/analyze",
        json={"product_description": "Test product"},
        headers=headers,
    )

    assert resp.status_code == 201
    data = resp.json()
    assert "task_id" in data
    task_id = data['task_id']
    print(f"✅ Task created: {task_id}")

    # 等待一小段时间让异步任务执行
    print("⏳ Waiting for task to process...")
    await asyncio.sleep(0.5)

    # 检查任务状态
    print("📝 Checking task status...")
    status_resp = await client.get(f"/api/status/{task_id}", headers=headers)
    print(f"Status response: {status_resp.status_code}")
    if status_resp.status_code == 200:
        status_data = status_resp.json()
        print(f"Task status: {status_data.get('status')}")
        print(f"Full status: {status_data}")

    # 尝试等待完成（短超时）
    print("⏳ Waiting for completion...")
    try:
        result = await wait_for_task_completion(client, token, task_id, timeout=5.0)
        print(f"✅ Task completed: {result}")
    except TimeoutError as e:
        print(f"❌ Timeout: {e}")
        raise

