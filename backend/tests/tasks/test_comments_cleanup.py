from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from app.services.comments_ingest import persist_comments

from app.db.session import SessionFactory
from app.tasks.maintenance_task import cleanup_expired_comments_impl


@pytest.mark.asyncio
async def test_cleanup_expired_comments_removes_labels_entities_and_rows() -> None:
    async with SessionFactory() as session:
        now = datetime.now(timezone.utc)
        # insert two comments: one expired, one active
        # 用正式入口写入，保证兼容（函数内部会兼容无 expires_at 的库）
        await persist_comments(
            session,
            source_post_id="p1",
            subreddit="r/test",
            comments=[
                {
                    "id": "t1_expired",
                    "body": "old",
                    "created_utc": (now - timedelta(days=200)).timestamp(),
                    "depth": 0,
                    "score": 1,
                    "captured_at": now - timedelta(days=200),
                },
                {
                    "id": "t1_active",
                    "body": "new",
                    "created_utc": (now - timedelta(days=1)).timestamp(),
                    "depth": 0,
                    "score": 1,
                    "captured_at": now - timedelta(days=1),
                },
            ],
        )
        # fetch ids
        res = await session.execute(text("SELECT id FROM comments WHERE reddit_comment_id='t1_expired'"))
        expired_id = int(res.scalar())
        res2 = await session.execute(text("SELECT id FROM comments WHERE reddit_comment_id='t1_active'"))
        active_id = int(res2.scalar())

        # attach labels/entities
        await session.execute(
            text(
                "INSERT INTO content_labels (content_type, content_id, category, aspect, confidence) VALUES ('comment', :cid, 'pain', 'other', 80)"
            ),
            {"cid": expired_id},
        )
        await session.execute(
            text(
                "INSERT INTO content_entities (content_type, content_id, entity, entity_type, count) VALUES ('comment', :cid, 'x', 'brand', 1)"
            ),
            {"cid": expired_id},
        )
        await session.commit()

    # run cleanup
    result = await cleanup_expired_comments_impl(skip_guard=True)
    assert result["deleted_comments"] >= 1

    async with SessionFactory() as session:
        # expired gone
        r = await session.execute(text("SELECT count(*) FROM comments WHERE reddit_comment_id='t1_expired'"))
        assert int(r.scalar()) == 0
        # labels/entities gone
        r2 = await session.execute(text("SELECT count(*) FROM content_labels WHERE content_type='comment' AND content_id=:id"), {"id": expired_id})
        assert int(r2.scalar()) == 0
        r3 = await session.execute(text("SELECT count(*) FROM content_entities WHERE content_type='comment' AND content_id=:id"), {"id": expired_id})
        assert int(r3.scalar()) == 0
        # active remains
        r4 = await session.execute(text("SELECT count(*) FROM comments WHERE id=:id"), {"id": active_id})
        assert int(r4.scalar()) == 1


@pytest.mark.asyncio
async def test_cleanup_uses_captured_at_not_created_utc() -> None:
    """
    关键用例：当 expires_at 为空时，应使用 captured_at 判断是否过期，不能用 created_utc。
    构造：created_utc 很久以前，但 captured_at 是最近抓到的数据，应当保留。
    """
    now = datetime.now(timezone.utc)

    # 先清理可能存在的测试数据
    async with SessionFactory() as session:
        await session.execute(
            text("DELETE FROM comments WHERE reddit_comment_id='t1_fallback_recent_capture'")
        )
        await session.commit()

    async with SessionFactory() as session:
        # 直接写入一条记录，expires_at=NULL，created_utc 很久之前，captured_at 近两天
        await session.execute(
            text(
                """
                INSERT INTO comments (
                    reddit_comment_id, source, source_post_id, subreddit,
                    parent_id, depth, body, author_id, author_name, author_created_utc,
                    created_utc, score, is_submitter, distinguished, edited,
                    permalink, removed_by_category, awards_count, captured_at, expires_at
                ) VALUES (
                    :rid, 'reddit', 'p-fallback', 'r/test',
                    NULL, 0, 'fallback', NULL, NULL, NULL,
                    :created_utc, 0, false, NULL, false,
                    NULL, NULL, 0, :captured_at, NULL
                )
                """
            ),
            {
                "rid": "t1_fallback_recent_capture",
                "created_utc": now - timedelta(days=400),
                "captured_at": now - timedelta(days=2),
            },
        )
        await session.commit()

    # 跑清理（跳过安全门，仅用于测试）
    _ = await cleanup_expired_comments_impl(skip_guard=True)

    async with SessionFactory() as session:
        r = await session.execute(
            text("SELECT count(*) FROM comments WHERE reddit_comment_id='t1_fallback_recent_capture'")
        )
        # 不应被清理
        assert int(r.scalar()) == 1
