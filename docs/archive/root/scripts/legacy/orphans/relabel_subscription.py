#!/usr/bin/env python3
"""
重标 subscription 相关记录为细分 Aspect（sub_cancel/sub_hidden_fee/sub_auto_renew/sub_price）。

默认一次处理 50,000 条，优先 comments；文本缺失时尝试 posts_raw。
"""
from __future__ import annotations

import argparse
import asyncio
from typing import Optional

from sqlalchemy import text

from app.db.session import SessionFactory
from app.services.text_classifier import classify_category_aspect


async def relabel_subscription_batch(limit: int, offset: int) -> int:
    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT cl.id,
                       CASE
                         WHEN cl.content_type = 'comment' THEN (SELECT body FROM comments WHERE id = cl.content_id)
                         ELSE (SELECT COALESCE(title,'') || ' ' || COALESCE(body,'') FROM posts_raw WHERE id = cl.content_id)
                       END AS text
                FROM content_labels cl
                WHERE cl.aspect = 'subscription'
                  AND cl.category = 'pain'
                ORDER BY cl.id
                LIMIT :lim OFFSET :off
                """
            ),
            {"lim": limit, "off": offset},
        )
        items = rows.fetchall()
        updates = []
        for row in items:
            text_val: Optional[str] = row.text
            if not text_val:
                continue
            new_cls = classify_category_aspect(text_val)
            new_aspect = new_cls.aspect.value
            if new_aspect != "subscription":
                updates.append({"id": row.id, "aspect": new_aspect})

        if updates:
            stmt = text("UPDATE content_labels SET aspect = :aspect WHERE id = :id")
            chunk = 200
            for i in range(0, len(updates), chunk):
                await session.execute(stmt, updates[i : i + chunk])
                await session.commit()
        return len(updates)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Relabel subscription records to sub_* aspects.")
    parser.add_argument("--limit", type=int, default=50000, help="Rows per batch")
    parser.add_argument("--offset", type=int, default=0, help="Offset for starting row")
    args = parser.parse_args()

    updated = await relabel_subscription_batch(args.limit, args.offset)
    print(f"✅ Relabeled subscription rows: {updated} (limit={args.limit}, offset={args.offset})")


if __name__ == "__main__":
    asyncio.run(main())
