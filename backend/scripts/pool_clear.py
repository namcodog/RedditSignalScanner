from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import delete

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool


async def main() -> None:
    parser = argparse.ArgumentParser(description="Clear community_pool (and optionally community_cache)")
    parser.add_argument("--cache-too", action="store_true", help="Also clear community_cache table")
    args = parser.parse_args()

    async with SessionFactory() as db:
        # hard delete all rows for isolation
        await db.execute(delete(CommunityPool))
        if args.cache_too:
            await db.execute(delete(CommunityCache))
        await db.commit()
        print("✅ Cleared community_pool" + (" and community_cache" if args.cache_too else ""))


if __name__ == "__main__":
    asyncio.run(main())

