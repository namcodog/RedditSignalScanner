from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models.community_pool import PendingCommunity
from app.models.posts_storage import Base as PostsBase, PostRaw
from app.models.task import Task
from app.models.user import User


@pytest.mark.asyncio
async def test_pending_community_requires_existing_task(db_session):
    pending = PendingCommunity(
        name="r/example",
        discovered_count=1,
        first_discovered_at=datetime.now(timezone.utc),
        last_discovered_at=datetime.now(timezone.utc),
        status="pending",
        discovered_from_task_id=uuid.uuid4(),
    )

    db_session.add(pending)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_pending_community_task_reference_set_null(db_session):
    user = User(email="cascade@example.com", password_hash=hash_password("SecurePass123!"))
    task = Task(user=user, product_description="Test product description long enough")

    db_session.add_all([user, task])
    await db_session.flush()

    pending = PendingCommunity(
        name="r/cascade",
        discovered_count=1,
        first_discovered_at=datetime.now(timezone.utc),
        last_discovered_at=datetime.now(timezone.utc),
        status="pending",
        discovered_from_task_id=task.id,
    )

    db_session.add(pending)
    await db_session.commit()

    await db_session.delete(task)
    await db_session.commit()

    await db_session.refresh(pending)
    assert pending.discovered_from_task_id is None


# 测试已删除: CommunityImportHistory 表已移除（功能孤岛清理）
# @pytest.mark.asyncio
# async def test_import_history_user_reference_set_null_on_delete(db_session):
#     ...


@pytest.mark.asyncio
async def test_post_raw_valid_to_is_timezone_aware(db_session):
    async with db_session.bind.begin() as conn:
        await conn.run_sync(PostsBase.metadata.create_all)

    post = PostRaw(
        source="reddit",
        source_post_id="abc123",
        version=1,
        created_at=datetime.now(timezone.utc),
        title="Sample",
        subreddit="sample_subreddit",
    )

    db_session.add(post)
    await db_session.flush()

    assert post.valid_to.tzinfo is not None
    assert post.valid_to.tzinfo.utcoffset(post.valid_to) is not None
