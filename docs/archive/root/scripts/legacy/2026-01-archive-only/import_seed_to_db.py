from __future__ import annotations

import asyncio

from app.db.session import SessionFactory
from app.services.community_pool_loader import CommunityPoolLoader


async def main() -> None:
    async with SessionFactory() as db:
        loader = CommunityPoolLoader(db)
        stats = await loader.load_seed_communities()
        print(f"✅ Seed communities loaded successfully!")
        print(f"   - Total in file: {stats['total_in_file']}")
        print(f"   - Newly loaded: {stats['loaded']}")
        print(f"   - Updated: {stats['updated']}")
        print(f"   - Total in DB: {stats['total_in_db']}")


if __name__ == "__main__":
    asyncio.run(main())

