from __future__ import annotations

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory


@pytest.mark.asyncio
async def test_authors_and_snapshots_tables_exist() -> None:
    async with SessionFactory() as session:
        for tbl in ("authors", "subreddit_snapshots"):
            res = await session.execute(text("SELECT to_regclass(:t) IS NOT NULL"), {"t": f"public.{tbl}"})
            assert res.scalar() is True, f"{tbl} should exist"

