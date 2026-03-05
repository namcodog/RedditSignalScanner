from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.security import hash_password
from app.models.community_pool import CommunityPool
from app.models.discovered_community import DiscoveredCommunity
from app.models.posts_storage import Base as PostsBase, PostRaw
from app.models.task import Task
from app.models.user import User
from app.services.community.community_category_map_service import replace_community_category_map


@pytest.mark.asyncio
async def test_discovered_community_requires_existing_task(db_session):
    pending = DiscoveredCommunity(
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
async def test_discovered_community_task_reference_set_null(db_session):
    user = User(email="cascade@example.com", password_hash=hash_password("SecurePass123!"))
    task = Task(user=user, product_description="Test product description long enough")

    community = CommunityPool(
        name="r/cascade",
        tier="core",
        categories={"source": "seed"},
        description_keywords={"keywords": ["test"]},
        daily_posts=5,
        avg_comment_length=120,
        quality_score=0.75,
        priority="high",
        is_active=True,
    )

    db_session.add_all([user, task, community])
    await db_session.flush()

    pending = DiscoveredCommunity(
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

    community = CommunityPool(
        name="r/sample_subreddit",
        tier="core",
        categories={"source": "seed"},
        description_keywords={"keywords": ["test"]},
        daily_posts=5,
        avg_comment_length=120,
        quality_score=0.75,
        priority="high",
        is_active=True,
    )
    db_session.add(community)
    await db_session.flush()

    post = PostRaw(
        source="reddit",
        source_post_id="abc123",
        version=1,
        created_at=datetime.now(timezone.utc),
        title="Sample title long enough",
        subreddit="r/sample_subreddit",
        community_id=community.id,
    )

    db_session.add(post)
    await db_session.flush()

    assert post.valid_to.tzinfo is not None
    assert post.valid_to.tzinfo.utcoffset(post.valid_to) is not None


@pytest.mark.asyncio
async def test_community_category_map_primary_unique(db_session):
    community = CommunityPool(
        name="r/test_primary_unique",
        tier="core",
        categories={"source": "seed"},
        description_keywords={"keywords": ["test"]},
        daily_posts=5,
        avg_comment_length=120,
        quality_score=0.75,
        priority="high",
        is_active=True,
    )
    db_session.add(community)
    await db_session.flush()

    await db_session.execute(
        text(
            """
            INSERT INTO business_categories (key, display_name)
            VALUES (:key, :name)
            ON CONFLICT (key) DO NOTHING
            """
        ),
        {"key": "Ecommerce_Business", "name": "Ecommerce Business"},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO business_categories (key, display_name)
            VALUES (:key, :name)
            ON CONFLICT (key) DO NOTHING
            """
        ),
        {"key": "Home_Lifestyle", "name": "Home Lifestyle"},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO community_category_map (community_id, category_key, is_primary)
            VALUES (:community_id, :category_key, true)
            """
        ),
        {"community_id": community.id, "category_key": "Ecommerce_Business"},
    )
    await db_session.commit()

    with pytest.raises(IntegrityError):
        await db_session.execute(
            text(
                """
                INSERT INTO community_category_map (community_id, category_key, is_primary)
                VALUES (:community_id, :category_key, true)
                """
            ),
            {"community_id": community.id, "category_key": "Home_Lifestyle"},
        )
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_posts_raw_missing_community_quarantines(db_session):
    source_post_id = f"missing-{uuid.uuid4().hex[:10]}"
    subreddit = f"r/missing_{uuid.uuid4().hex[:6]}"

    await db_session.execute(
        text("DELETE FROM posts_quarantine WHERE source_post_id = :source_post_id"),
        {"source_post_id": source_post_id},
    )
    await db_session.commit()

    await db_session.execute(
        text(
            """
            INSERT INTO posts_raw
                (source, source_post_id, created_at, title, body, subreddit, author_name)
            VALUES
                (:source, :source_post_id, :created_at, :title, :body, :subreddit, :author_name)
            """
        ),
        {
            "source": "reddit",
            "source_post_id": source_post_id,
            "created_at": datetime.now(timezone.utc),
            "title": "Valid title for quarantine test",
            "body": "Valid body content long enough for quarantine test.",
            "subreddit": subreddit,
            "author_name": "tester",
        },
    )
    await db_session.commit()

    raw_count = await db_session.execute(
        text("SELECT COUNT(*) FROM posts_raw WHERE source_post_id = :source_post_id"),
        {"source_post_id": source_post_id},
    )
    quarantine_count = await db_session.execute(
        text(
            "SELECT COUNT(*) FROM posts_quarantine WHERE source_post_id = :source_post_id"
        ),
        {"source_post_id": source_post_id},
    )

    assert raw_count.scalar_one() == 0
    assert quarantine_count.scalar_one() == 1

    quarantine_id = await db_session.execute(
        text(
            """
            SELECT id
            FROM posts_quarantine
            WHERE source_post_id = :source_post_id
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"source_post_id": source_post_id},
    )
    quarantine_id_value = quarantine_id.scalar_one()
    audit_count = await db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM data_audit_events
            WHERE event_type = 'quarantine'
              AND target_type = 'posts_quarantine'
              AND target_id = :target_id
            """
        ),
        {"target_id": str(quarantine_id_value)},
    )
    assert audit_count.scalar_one() == 1


@pytest.mark.asyncio
async def test_block_direct_community_pool_categories_update(db_session):
    community = CommunityPool(
        name="r/guard_categories",
        tier="core",
        categories={},
        description_keywords={"keywords": ["test"]},
        daily_posts=5,
        avg_comment_length=120,
        quality_score=0.75,
        priority="high",
        is_active=True,
    )
    db_session.add(community)
    await db_session.flush()

    with pytest.raises(DBAPIError):
        await db_session.execute(
            text(
                """
                UPDATE community_pool
                SET categories = :payload
                WHERE id = :community_id
                """
            ),
            {"payload": '{"test": ["blocked"]}', "community_id": community.id},
        )
        await db_session.commit()

    await db_session.rollback()

    await db_session.execute(text("SET LOCAL app.allow_category_cache_update = '1'"))
    await db_session.execute(
        text(
            """
            UPDATE community_pool
            SET categories = :payload
            WHERE id = :community_id
            """
        ),
        {"payload": '{"test": ["allowed"]}', "community_id": community.id},
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_category_alias_normalized_to_ecommerce_business(db_session):
    community = CommunityPool(
        name="r/alias_categories",
        tier="core",
        categories={"primary": ["E-commerce_Ops"]},
        description_keywords={"keywords": ["test"]},
        daily_posts=5,
        avg_comment_length=120,
        quality_score=0.75,
        priority="high",
        is_active=True,
    )
    db_session.add(community)
    await db_session.flush()

    await db_session.execute(
        text(
            """
            INSERT INTO business_categories (key, display_name)
            VALUES (:key, :name)
            ON CONFLICT (key) DO NOTHING
            """
        ),
        {"key": "Ecommerce_Business", "name": "Ecommerce Business"},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO business_categories (key, display_name)
            VALUES (:key, :name)
            ON CONFLICT (key) DO NOTHING
            """
        ),
        {"key": "E-commerce_Ops", "name": "E-commerce Ops"},
    )
    await db_session.commit()

    await replace_community_category_map(
        db_session,
        community_id=community.id,
        categories={"primary": ["E-commerce_Ops"]},
    )
    await db_session.commit()

    res = await db_session.execute(
        text(
            """
            SELECT category_key, is_primary
            FROM community_category_map
            WHERE community_id = :community_id
            """
        ),
        {"community_id": community.id},
    )
    rows = res.mappings().all()
    assert rows == [{"category_key": "Ecommerce_Business", "is_primary": True}]


@pytest.mark.asyncio
async def test_posts_raw_current_unique(db_session):
    community = CommunityPool(
        name="r/test_current_unique",
        tier="core",
        categories={"primary": ["Ecommerce_Business"]},
        description_keywords={"keywords": ["test"]},
        daily_posts=3,
        avg_comment_length=110,
        quality_score=0.65,
        priority="medium",
        is_active=True,
    )
    db_session.add(community)
    await db_session.flush()

    source_post_id = f"dup-{uuid.uuid4().hex[:8]}"
    common_fields = {
        "source": "reddit",
        "source_post_id": source_post_id,
        "created_at": datetime.now(timezone.utc),
        "title": "Valid title for uniqueness test",
        "body": "Valid body content long enough for uniqueness test.",
        "subreddit": community.name,
        "community_id": community.id,
        "author_name": "tester",
        "is_current": True,
    }

    await db_session.execute(
        text(
            """
            INSERT INTO posts_raw
                (source, source_post_id, version, created_at, title, body, subreddit, community_id, author_name, is_current)
            VALUES
                (:source, :source_post_id, :version, :created_at, :title, :body, :subreddit, :community_id, :author_name, :is_current)
            """
        ),
        {**common_fields, "version": 1},
    )
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text(
                """
                INSERT INTO posts_raw
                    (source, source_post_id, version, created_at, title, body, subreddit, community_id, author_name, is_current)
                VALUES
                    (:source, :source_post_id, :version, :created_at, :title, :body, :subreddit, :community_id, :author_name, :is_current)
                """
            ),
            {**common_fields, "version": 2},
        )
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_post_semantic_labels_has_provenance_columns(db_session):
    columns = await db_session.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'post_semantic_labels'
            """
        )
    )
    column_set = {row[0] for row in columns.fetchall()}
    assert "rule_version" in column_set
    assert "llm_version" in column_set
