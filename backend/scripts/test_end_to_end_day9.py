from __future__ import annotations

"""
Day 9 end-to-end verification script.

Validates:
1. Registration + Bearer token authentication
2. Full analysis workflow performance and signal thresholds
3. SSE stream authentication with Bearer token
"""

import asyncio
import time
from typing import Any, Dict

import httpx

BASE_URL = "http://localhost:8006"


async def test_full_analysis_with_signals() -> bool:
    """Run the full analysis pipeline and validate Day 9 acceptance criteria."""
    print("🚀 开始Day 9端到端测试...")

    async with httpx.AsyncClient(timeout=300.0) as client:
        print("1️⃣ 注册用户...")
        register_resp = await client.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": f"day9-e2e-{int(time.time())}@example.com",
                "password": "Test1234",  # 至少8个字符
            },
        )
        register_resp.raise_for_status()
        token = register_resp.json()["access_token"]
        print(f"✅ Token获取成功: {token[:20]}...")

        headers = {"Authorization": f"Bearer {token}"}
        print("2️⃣ 创建分析任务...")
        analyze_resp = await client.post(
            f"{BASE_URL}/api/analyze",
            headers=headers,
            json={"product_description": "AI-powered note-taking app for researchers"},
        )
        analyze_resp.raise_for_status()
        task_id = analyze_resp.json()["task_id"]
        print(f"✅ 任务创建成功: {task_id}")

        print("3️⃣ 等待任务完成...")
        start_time = time.time()
        max_wait = 300

        while True:
            status_resp = await client.get(f"{BASE_URL}/api/status/{task_id}", headers=headers)
            status_resp.raise_for_status()
            status_data: Dict[str, Any] = status_resp.json()

            if status_data["status"] == "completed":
                print("✅ 任务完成")
                break
            if status_data["status"] == "failed":
                raise RuntimeError(f"❌ 任务失败: {status_data.get('error')}")

            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise TimeoutError(f"❌ 任务超时: {elapsed:.2f}秒 > {max_wait}秒")

            print(f"   进度: {status_data.get('progress', 0)}% - {elapsed:.1f}秒")
            await asyncio.sleep(3)

        duration = time.time() - start_time

        print("4️⃣ 获取分析报告...")
        report_resp = await client.get(f"{BASE_URL}/api/report/{task_id}", headers=headers)
        report_resp.raise_for_status()
        report = report_resp.json()

        print("5️⃣ 验证信号数据...")
        payload = report.get("report", {})
        pain_points = payload.get("pain_points", [])
        competitors = payload.get("competitors", [])
        opportunities = payload.get("opportunities", [])

        print("\n📊 分析结果:")
        print(f"   ⏱️  耗时: {duration:.2f}秒")
        print(f"   😣 痛点数: {len(pain_points)}")
        print(f"   🏢 竞品数: {len(competitors)}")
        print(f"   💡 机会数: {len(opportunities)}")

        print("\n✅ 验收标准检查:")
        assert duration < 270, f"❌ 耗时超标: {duration:.2f}秒 > 270秒"
        print(f"   ✅ 性能达标: {duration:.2f}秒 < 270秒")

        assert len(pain_points) >= 5, f"❌ 痛点数不足: {len(pain_points)} < 5"
        print(f"   ✅ 痛点数达标: {len(pain_points)} >= 5")

        assert len(competitors) >= 3, f"❌ 竞品数不足: {len(competitors)} < 3"
        print(f"   ✅ 竞品数达标: {len(competitors)} >= 3")

        assert len(opportunities) >= 3, f"❌ 机会数不足: {len(opportunities)} < 3"
        print(f"   ✅ 机会数达标: {len(opportunities)} >= 3")

        print("\n📋 数据结构验证:")
        if pain_points:
            assert "description" in pain_points[0], "痛点缺少description字段"
            assert "frequency" in pain_points[0], "痛点缺少frequency字段"
            print("   ✅ 痛点数据结构完整")

        if competitors:
            assert "name" in competitors[0], "竞品缺少name字段"
            assert "mentions" in competitors[0], "竞品缺少mentions字段"
            print("   ✅ 竞品数据结构完整")

        if opportunities:
            assert "description" in opportunities[0], "机会缺少description字段"
            assert "relevance_score" in opportunities[0], "机会缺少relevance_score字段"
            print("   ✅ 机会数据结构完整")

        print("\n🎉 所有验收标准通过!")
        return True


async def test_sse_with_bearer_token() -> None:
    """Validate SSE stream authentication via Bearer token."""
    print("\n🔐 测试SSE认证...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        register_resp = await client.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": f"day9-sse-{int(time.time())}@example.com",
                "password": "Test123",
            },
        )
        register_resp.raise_for_status()
        token = register_resp.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        analyze_resp = await client.post(
            f"{BASE_URL}/api/analyze",
            headers=headers,
            json={"product_description": "test"},
        )
        analyze_resp.raise_for_status()
        task_id = analyze_resp.json()["task_id"]

        async with client.stream(
            "GET",
            f"{BASE_URL}/api/analyze/stream/{task_id}",
            headers=headers,
        ) as response:
            response.raise_for_status()
            print("✅ SSE Bearer token认证成功")

            event_count = 0
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    event_count += 1
                    print(f"   收到事件: {line[:50]}...")
                    if event_count >= 3:
                        break

            assert event_count > 0, "未收到SSE事件"
            print(f"✅ SSE事件流正常 (收到{event_count}个事件)")


if __name__ == "__main__":
    print("=" * 60)
    print("Day 9 端到端测试")
    print("=" * 60)

    try:
        asyncio.run(test_full_analysis_with_signals())
        asyncio.run(test_sse_with_bearer_token())
        print("\n" + "=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)
    except Exception as exc:  # pragma: no cover - manual script
        print(f"\n❌ 测试失败: {exc}")
        raise
