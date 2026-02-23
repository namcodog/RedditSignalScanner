from __future__ import annotations

import argparse
import asyncio
import os
from urllib.parse import urlparse

from sqlalchemy import delete

from app.db.session import SessionFactory, DATABASE_URL
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool


def _is_main_database() -> bool:
    """判断当前是否指向主库 reddit_signal_scanner。"""
    url = DATABASE_URL or ""
    # 去掉 +asyncpg 之类的驱动后缀
    url = url.replace("+asyncpg", "")
    parsed = urlparse(url)
    db_name = (parsed.path or "").lstrip("/") or ""
    return db_name == "reddit_signal_scanner"


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clear community_pool (and optionally community_cache)"
    )
    parser.add_argument(
        "--cache-too",
        action="store_true",
        help="Also clear community_cache table",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip safety guard (required on main DB)",
    )
    args = parser.parse_args()

    # 保护开关：默认禁止在主库上误删，除非显式加 --force。
    protect_enabled = os.getenv("POOL_CLEAR_PROTECT", "1") != "0"
    if protect_enabled and not args.force and _is_main_database():
        print(
            "❌ 安全保护：检测到数据库名称为 'reddit_signal_scanner'，"
            "未指定 --force，已取消清空 community_pool/community_cache。",
            flush=True,
        )
        return

    async with SessionFactory() as db:
        # hard delete all rows for isolation
        await db.execute(delete(CommunityPool))
        if args.cache_too:
            await db.execute(delete(CommunityCache))
        await db.commit()
        print(
            "✅ Cleared community_pool"
            + (" and community_cache" if args.cache_too else "")
        )


if __name__ == "__main__":
    asyncio.run(main())
