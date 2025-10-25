"""
存储层维护任务验收：
1. storage_metrics 采集入库
2. posts_archive 归档函数
3. 存储容量预警
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select, text

from app.db.session import SessionFactory
from app.models.posts_storage import PostRaw
from app.tasks import maintenance_task


@pytest.mark.asyncio
async def test_collect_storage_metrics_impl_inserts_snapshot() -> None:
    async with SessionFactory() as session:
        await session.execute(text("DELETE FROM storage_metrics"))
        await session.commit()

    result = await maintenance_task.collect_storage_metrics_impl()

    assert result["status"] == "completed"
    assert "collected_at" in result

    async with SessionFactory() as session:
        stored = await session.execute(text("SELECT COUNT(*) FROM storage_metrics"))
        assert stored.scalar_one() == 1


@pytest.mark.asyncio
async def test_archive_old_posts_impl_moves_rows() -> None:
    async with SessionFactory() as session:
        await session.execute(text("DELETE FROM posts_archive"))
        await session.execute(
            delete(PostRaw).where(PostRaw.source_post_id.like("archive-test%"))
        )
        await session.commit()

        now = datetime.now(timezone.utc)
        archived = PostRaw(
            source="reddit",
            source_post_id="archive-test-1",
            version=1,
            created_at=now - timedelta(days=120),
            fetched_at=now - timedelta(days=119),
            valid_from=now - timedelta(days=120),
            valid_to=now - timedelta(days=110),
            is_current=False,
            title="Archived",
            body="archived body",
            subreddit="archive",
            score=1,
            num_comments=0,
        )
        session.add(archived)
        await session.commit()

    result = await maintenance_task.archive_old_posts_impl(
        retention_days=30, batch_size=100
    )

    assert result["status"] == "completed"
    assert result["archived_count"] >= 1

    async with SessionFactory() as session:
        count = await session.execute(
            text(
                "SELECT COUNT(*) FROM posts_archive WHERE source_post_id = 'archive-test-1'"
            )
        )
        assert count.scalar_one() >= 1


@pytest.mark.asyncio
async def test_check_storage_capacity_impl_returns_sizes() -> None:
    result = await maintenance_task.check_storage_capacity_impl(threshold_gb=1000.0)

    assert "database_size_gb" in result
    assert "posts_raw_size_gb" in result
    assert "posts_hot_size_gb" in result
    assert result["threshold_gb"] == 1000.0
