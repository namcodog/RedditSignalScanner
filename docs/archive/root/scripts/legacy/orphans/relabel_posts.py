#!/usr/bin/env python3
"""
批量重标 posts_raw 的 aspect。
逻辑复用 relabel_aspect_only.py，但针对 posts_raw 和 content_type='post'。
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import text

from app.db.session import SessionFactory
from app.services.text_classifier import classify_category_aspect


async def relabel_posts_batch(limit: int, offset: int) -> int:
    async with SessionFactory() as session:
        # 1. 获取 content_labels 中 content_type='post' 的记录
        rows = await session.execute(
            text(
                """
                SELECT cl.id, cl.aspect, cl.category, p.title, p.body
                FROM content_labels cl
                JOIN posts_raw p ON p.id = cl.content_id
                WHERE cl.content_type = 'post'
                ORDER BY cl.id
                LIMIT :lim OFFSET :off
                """
            ),
            {"lim": limit, "off": offset},
        )
        updates = []
        for row in rows.fetchall():
            # 组合 title + body 进行分类
            text_content = f"{row.title or ''} {row.body or ''}".strip()
            new_cls = classify_category_aspect(text_content)
            
            if new_cls.aspect.value != row.aspect or new_cls.category.value != row.category:
                updates.append({
                    "id": row.id, 
                    "aspect": new_cls.aspect.value,
                    "category": new_cls.category.value
                })

        if updates:
            chunk_size = 100
            stmt = text(
                """
                UPDATE content_labels
                SET aspect = :aspect, category = :category
                WHERE id = :id
                """
            )
            for i in range(0, len(updates), chunk_size):
                chunk = updates[i : i + chunk_size]
                await session.execute(stmt, chunk)
                await session.commit()
        return len(updates)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Relabel POSTS in batches.")
    parser.add_argument("--limit", type=int, default=10000, help="Rows per batch")
    parser.add_argument("--offset", type=int, default=0, help="Offset for starting row")
    parser.add_argument("--max-offset", type=int, default=None, help="Process up to this offset")
    args = parser.parse_args()

    current_offset = args.offset
    total_updated = 0
    while True:
        updated = await relabel_posts_batch(args.limit, current_offset)
        total_updated += updated
        print(f"✅ Relabeled POST aspects: {updated} rows (limit={args.limit}, offset={current_offset})")
        if updated == 0:
            break
        current_offset += args.limit
        if args.max_offset is not None and current_offset >= args.max_offset:
            break

    print(f"🎯 Total updated POSTS: {total_updated}")


if __name__ == "__main__":
    asyncio.run(main())
