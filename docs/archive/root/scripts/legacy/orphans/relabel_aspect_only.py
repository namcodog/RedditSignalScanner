#!/usr/bin/env python3
"""
批量重标 content_labels.aspect（仅更新 aspect，不改 category）。

用法示例：
    PYTHONPATH=$(pwd)/backend python -m backend.scripts.relabel_aspect_only --limit 50000 --offset 0

默认：一次处理 10000 条，按 id 升序。
谨慎：运行前确保数据库备份，建议分批执行。
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import text

from app.db.session import SessionFactory
from app.services.text_classifier import classify_category_aspect


async def relabel_batch(limit: int, offset: int) -> int:
    async with SessionFactory() as session:
        rows = await session.execute(
            text(
                """
                SELECT cl.id, cl.category, cl.aspect, c.body
                FROM content_labels cl
                JOIN comments c ON c.id = cl.content_id
                WHERE cl.content_type = 'comment'
                ORDER BY cl.id
                LIMIT :lim OFFSET :off
                """
            ),
            {"lim": limit, "off": offset},
        )
        updates = []
        for row in rows.fetchall():
            new_cls = classify_category_aspect(row.body)
            # Update if either category or aspect changed
            if new_cls.category.value != row.category or new_cls.aspect.value != row.aspect:
                updates.append({
                    "id": row.id, 
                    "category": new_cls.category.value,
                    "aspect": new_cls.aspect.value
                })

        if updates:
            chunk_size = 100
            stmt = text(
                """
                UPDATE content_labels
                SET category = :category, aspect = :aspect
                WHERE id = :id
                """
            )
            for i in range(0, len(updates), chunk_size):
                chunk = updates[i : i + chunk_size]
                await session.execute(stmt, chunk)
                await session.commit()
        return len(updates)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Relabel content_labels.aspect in batches.")
    parser.add_argument("--limit", type=int, default=10000, help="Rows per batch")
    parser.add_argument("--offset", type=int, default=0, help="Offset for starting row")
    parser.add_argument("--max-offset", type=int, default=None, help="Process up to this offset (auto-loop)")
    args = parser.parse_args()

    current_offset = args.offset
    total_updated = 0
    while True:
        updated = await relabel_batch(args.limit, current_offset)
        total_updated += updated
        print(f"✅ Relabeled aspects: {updated} rows (limit={args.limit}, offset={current_offset})")
        if updated == 0:
            break
        current_offset += args.limit
        if args.max_offset is not None and current_offset >= args.max_offset:
            break

    print(f"🎯 Total updated: {total_updated} rows")


if __name__ == "__main__":
    asyncio.run(main())
