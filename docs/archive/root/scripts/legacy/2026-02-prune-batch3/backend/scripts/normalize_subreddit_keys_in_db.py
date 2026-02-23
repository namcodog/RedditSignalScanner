#!/usr/bin/env python3
from __future__ import annotations

"""
一次性规范化数据库中的 subreddit 命名：

- 规则：内部存储统一使用「去掉 r/ 前缀 + 全小写」的 key。
- 目标表：
    - posts_raw.subreddit
    - posts_hot.subreddit
    - comments.subreddit

当前观测到的脏数据主要是 comments 表中少量大写变体（例如 FulfillmentByAmazon）。

用法（在项目根目录执行）：
    cd backend
    python -u scripts/normalize_subreddit_keys_in_db.py

脚本会：
    1）打印每张表中违反规范的 subreddit 列表；
    2）对这些记录执行 UPDATE，将 subreddit 统一为 lower(subreddit)；
    3）打印修复后的统计。
"""

import asyncio

from sqlalchemy import text

from app.db.session import SessionFactory


async def _normalize_table_subreddit(table_name: str) -> int:
    """将指定表中的 subreddit 统一为小写（仅针对存在大小写不一致的记录）。"""
    async with SessionFactory() as session:
        # 先列出有哪些不规范的值，方便运维观察
        result = await session.execute(
            text(
                f"""
                SELECT DISTINCT subreddit
                FROM {table_name}
                WHERE subreddit <> lower(subreddit)
                ORDER BY subreddit
                """
            )
        )
        rows = [r[0] for r in result.fetchall()]
        if not rows:
            print(f"✅ {table_name}: 没有发现大小写不一致的 subreddit")
            return 0

        print(f"⚠️ {table_name}: 发现 {len(rows)} 个需要规范化的 subreddit 值：")
        for name in rows:
            print(f"   - {name!r} -> {name.lower()!r}")

        # 执行规范化 UPDATE
        update_result = await session.execute(
            text(
                f"""
                UPDATE {table_name}
                SET subreddit = lower(subreddit)
                WHERE subreddit <> lower(subreddit)
                """
            )
        )
        await session.commit()
        affected = update_result.rowcount or 0
        print(f"✅ {table_name}: 已规范化 {affected} 行\n")
        return affected


async def main() -> None:
    print("==========================================")
    print("规范化数据库中的 subreddit 命名")
    print("规则：去 r/ 前缀 + 全小写（此脚本只负责小写化现有值）")
    print("==========================================\n")

    total = 0
    for table in ("posts_raw", "posts_hot", "comments"):
        count = await _normalize_table_subreddit(table)
        total += count

    print("==========================================")
    print(f"完成：共规范化 {total} 行记录")
    print("==========================================")


if __name__ == "__main__":
    asyncio.run(main())

