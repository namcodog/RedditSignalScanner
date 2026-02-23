#!/usr/bin/env python3
"""检查评论表状态"""
import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import SessionFactory
from sqlalchemy import text


async def check_comments_status():
    async with SessionFactory() as session:
        # 总评论数
        r = await session.execute(text("SELECT COUNT(*) FROM comments"))
        total = r.scalar()
        print(f"📊 评论表总数: {total:,} 条")
        
        # 涉及社区数
        r2 = await session.execute(text("SELECT COUNT(DISTINCT subreddit) FROM comments"))
        subs = r2.scalar()
        print(f"📊 涉及社区数: {subs} 个")
        
        # Top 10 社区
        r3 = await session.execute(
            text("SELECT subreddit, COUNT(*) as cnt FROM comments GROUP BY subreddit ORDER BY cnt DESC LIMIT 10")
        )
        print(f"\n📈 Top 10 社区（按评论数）:")
        for row in r3.all():
            print(f"   {row[0]}: {row[1]:,} 条")
        
        # 深度分布
        r4 = await session.execute(
            text("SELECT depth, COUNT(*) as cnt FROM comments GROUP BY depth ORDER BY depth")
        )
        print(f"\n📊 评论深度分布:")
        for row in r4.all():
            print(f"   深度 {row[0]}: {row[1]:,} 条")
        
        # 最近24小时新增
        r5 = await session.execute(
            text("SELECT COUNT(*) FROM comments WHERE captured_at > NOW() - INTERVAL '24 hours'")
        )
        recent = r5.scalar()
        print(f"\n⏰ 最近24小时新增: {recent:,} 条")


if __name__ == "__main__":
    asyncio.run(check_comments_status())

