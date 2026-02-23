from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.tasks.maintenance_task import (
    cleanup_orphan_content_labels_entities_impl,
)


@pytest.mark.asyncio
async def test_cleanup_orphan_content_labels_entities_removes_orphans() -> None:
    async with SessionFactory() as db:
        # 准备：插入一条孤儿 label/entity 和一条有效引用
        await db.execute(text("TRUNCATE TABLE content_labels, content_entities RESTART IDENTITY CASCADE"))

        # 有效引用：需要 posts_hot/comments 中存在 id=1；这里使用防御性插入/忽略
        await db.execute(
            text(
                """
                INSERT INTO content_labels (content_type, content_id, category, aspect, confidence)
                VALUES ('post', 1, 'pain', 'price', 90)
                ON CONFLICT DO NOTHING
                """
            )
        )
        await db.execute(
            text(
                """
                INSERT INTO content_entities (content_type, content_id, entity, entity_type, count)
                VALUES ('post', 1, 'test', 'brand', 1)
                ON CONFLICT DO NOTHING
                """
            )
        )

        # 孤儿记录：引用一个不存在的 content_id
        await db.execute(
            text(
                """
                INSERT INTO content_labels (content_type, content_id, category, aspect, confidence)
                VALUES ('post', 999999, 'pain', 'price', 90)
                """
            )
        )
        await db.execute(
            text(
                """
                INSERT INTO content_entities (content_type, content_id, entity, entity_type, count)
                VALUES ('post', 999999, 'orphan', 'brand', 1)
                """
            )
        )
        await db.commit()

        before_labels = (
            await db.execute(
                text("SELECT COUNT(*) FROM content_labels WHERE content_id = 999999")
            )
        ).scalar_one()
        before_entities = (
            await db.execute(
                text("SELECT COUNT(*) FROM content_entities WHERE content_id = 999999")
            )
        ).scalar_one()
        assert before_labels == 1
        assert before_entities == 1

    result = await cleanup_orphan_content_labels_entities_impl(
        batch_size=2,
        max_batches=10,
        lock_timeout_ms=1000,
        statement_timeout_s=5,
    )
    assert result["status"] == "completed"
    assert result["deleted_labels"] >= 1
    assert result["deleted_entities"] >= 1
    assert result["batches"] >= 1

    async with SessionFactory() as db:
        after_labels = (
            await db.execute(
                text("SELECT COUNT(*) FROM content_labels WHERE content_id = 999999")
            )
        ).scalar_one()
        after_entities = (
            await db.execute(
                text("SELECT COUNT(*) FROM content_entities WHERE content_id = 999999")
            )
        ).scalar_one()

        assert after_labels == 0
        assert after_entities == 0
