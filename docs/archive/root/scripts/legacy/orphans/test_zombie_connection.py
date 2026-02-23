#!/usr/bin/env python3
"""
测试脚本：故意制造僵尸连接，验证数据库超时配置是否生效
"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import SessionFactory


async def create_zombie_connection():
    """故意创建一个僵尸连接（开启事务但不提交也不回滚）"""
    print("🧟 开始创建僵尸连接...")

    from sqlalchemy import text

    async with SessionFactory() as session:
        # 开启事务
        await session.execute(text("BEGIN;"))
        print("✅ 事务已开启（BEGIN）")

        # 执行一个简单查询
        result = await session.execute(text("SELECT 1 as test;"))
        row = result.fetchone()
        print(f"✅ 查询执行成功: {row}")

        # 故意不 commit 也不 rollback，让连接保持在 "idle in transaction" 状态
        print("⏳ 保持连接在 'idle in transaction' 状态...")
        print("⏳ 等待 90 秒，观察数据库是否会在 60 秒后自动回滚...")

        # 等待 90 秒（超过 60 秒的超时配置）
        await asyncio.sleep(90)

        print("⏰ 90 秒已过，尝试再次查询...")

        try:
            # 尝试再次查询（如果超时配置生效，这里应该会失败）
            result = await session.execute(text("SELECT 2 as test;"))
            row = result.fetchone()
            print(f"❌ 查询仍然成功: {row} （超时配置可能未生效）")
        except Exception as e:
            print(f"✅ 查询失败（符合预期）: {e}")
            print("✅ 数据库超时配置已生效！连接已被自动回滚+断开")


async def main():
    print("=" * 60)
    print("测试数据库超时配置")
    print("=" * 60)
    print()
    
    try:
        await create_zombie_connection()
    except Exception as e:
        print(f"✅ 连接被强制断开（符合预期）: {e}")
        print("✅ 数据库超时配置已生效！")
    
    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

