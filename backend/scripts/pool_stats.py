from __future__ import annotations

import asyncio
from typing import Dict

from sqlalchemy import func, select, cast, String

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool


async def main() -> None:
    async with SessionFactory() as db:
        # Total
        total = (await db.execute(select(func.count()).select_from(CommunityPool))).scalar_one()
        # By priority
        by_priority = (
            await db.execute(
                select(CommunityPool.priority, func.count()).group_by(CommunityPool.priority)
            )
        ).all()
        # Crossborder subset
        # categories is JSONB (list); use simple LIKE match for quick stats
        # Note: for production, use proper JSONB containment ops, but here LIKE is sufficient and portable.
        cross_total = (
            await db.execute(
                select(func.count()).select_from(CommunityPool).where(cast(CommunityPool.categories, String).like('%crossborder%'))
            )
        ).scalar_one()

        print("📊 Community Pool Stats")
        print(f"   - Total rows: {total}")
        print("   - By priority:")
        dist: Dict[str, int] = {str(k or ""): int(v) for k, v in by_priority}
        for k in sorted(dist.keys()):
            print(f"       {k or 'unknown'}: {dist[k]}")
        print(f"   - Crossborder tagged: {cross_total}")


if __name__ == "__main__":
    asyncio.run(main())
