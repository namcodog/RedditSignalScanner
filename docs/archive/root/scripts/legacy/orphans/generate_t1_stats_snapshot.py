#!/usr/bin/env python3
"""生成 T1 Stats 快照（reports/local-acceptance/t1-stats-snapshot.json）。"""
import asyncio
from pathlib import Path

from app.db.session import SessionFactory
from app.services.t1_stats import write_snapshot_to_file


async def main() -> None:
    async with SessionFactory() as session:
        path = await write_snapshot_to_file(session)
        print(f"✅ Stats snapshot written to {path}")


if __name__ == "__main__":
    asyncio.run(main())
