"""Quick metric: posts_hot growth over the last 7 days.

Reads DATABASE_URL from environment (backend/.env is auto-loaded by
app.core.config when SessionFactory is imported).

Usage:
    python -u backend/scripts/posts_growth_7d.py
"""

from __future__ import annotations

import asyncio
from typing import Any, Sequence

from sqlalchemy import text

from app.db.session import SessionFactory


async def _run() -> Sequence[tuple[str, int]]:
    query = text(
        """
        SELECT TO_CHAR(DATE(created_at), 'YYYY-MM-DD') AS day, COUNT(*) AS count
        FROM posts_hot
        WHERE created_at >= NOW() - INTERVAL '7 days'
        GROUP BY DATE(created_at)
        ORDER BY 1;
        """
    )

    async with SessionFactory() as db:
        result = await db.execute(query)
        rows = [(str(day), int(count)) for day, count in result]
        return rows


def main() -> None:
    rows = asyncio.run(_run())
    print("day,count")
    for day, count in rows:
        print(f"{day},{count}")


if __name__ == "__main__":
    main()

