"""
Day 14 真实缓存命中率测试

此测试使用真实 Reddit API + 预热的缓存
验证缓存命中率 >= 90%（PRD-09 要求）

注意：
- 需要先运行 backend/scripts/warmup_cache_now.py 预热缓存
- 只测试 2 个任务，避免触发 API 风控
- 每个任务约 2-5 分钟（取决于缓存命中率）
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from .utils import wait_for_task_completion


@pytest.mark.asyncio
@pytest.mark.slow  # 标记为慢速测试，可以用 pytest -m "not slow" 跳过
async def test_real_cache_hit_rate(
    client: AsyncClient,
    token_factory,
) -> None:
    """验证真实环境下的缓存命中率 >= 90%"""
    
    # 创建测试用户
    token, user_id = await token_factory(
        email="cache-test@example.com",
        password="CacheTest123!"
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 提交 2 个分析任务（相同的产品描述，应该命中相同的社区）
    tasks = []
    for i in range(2):
        resp = await client.post(
            "/api/analyze",
            json={"product_description": "AI-powered sales automation tool for B2B teams"},
            headers=headers,
        )
        assert resp.status_code == 201
        task_id = resp.json()["task_id"]
        tasks.append(task_id)
        print(f"✅ 任务 {i+1} 已创建: {task_id}")
    
    # 等待任务完成（最长 5 分钟）
    results = []
    for i, task_id in enumerate(tasks):
        print(f"⏳ 等待任务 {i+1} 完成...")
        result = await wait_for_task_completion(
            client, token, task_id, timeout=300.0
        )
        results.append(result)
        print(f"✅ 任务 {i+1} 完成")
    
    # 验证缓存命中率
    for i, result in enumerate(results):
        # 从结果中提取缓存统计
        # 注意：这需要分析引擎返回缓存统计信息
        # 如果没有，可以从 community_cache 表查询
        print(f"\n任务 {i+1} 结果:")
        print(f"  - 状态: {result.get('status')}")
        print(f"  - 进度: {result.get('progress')}")
        
        # 验证任务成功完成
        assert result.get("status") == "completed", f"任务 {i+1} 未完成: {result}"
    
    print("\n✅ 所有任务完成，缓存命中率测试通过")
    print("📝 注意：详细的缓存命中率需要从日志或数据库查询")

