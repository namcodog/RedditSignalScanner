"""
测试冷热双写功能
验证 posts_raw 和 posts_hot 表的数据写入
"""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.posts_storage import PostHot, PostRaw


async def test_cold_hot_dual_write():
    """测试冷热双写功能"""
    # 1. 创建数据库连接
    DATABASE_URL = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner"
    )
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("=" * 60)
        print("🧪 测试冷热双写功能")
        print("=" * 60)
        print()

        # 2. 准备测试数据
        test_post_id = "test_post_001"
        test_subreddit = "r/test_community"
        test_title = "Test Post for Cold-Hot Dual Write"
        test_body = "This is a test post to verify cold-hot dual write functionality."
        test_created_at = datetime.now(timezone.utc)

        print(f"📝 测试数据:")
        print(f"   - Post ID: {test_post_id}")
        print(f"   - Subreddit: {test_subreddit}")
        print(f"   - Title: {test_title}")
        print()

        # 3. 写入冷库 (posts_raw)
        print("=" * 60)
        print("1️⃣  写入冷库 (posts_raw)")
        print("=" * 60)

        cold_post = PostRaw(
            source="reddit",
            source_post_id=test_post_id,
            version=1,
            created_at=test_created_at,
            fetched_at=datetime.now(timezone.utc),
            title=test_title,
            body=test_body,
            subreddit=test_subreddit,
            score=100,
            num_comments=50,
            author_id="test_author_001",
            author_name="test_author",
        )

        session.add(cold_post)
        await session.commit()
        print("✅ 冷库写入成功")
        print()

        # 4. 验证冷库写入
        result = await session.execute(
            select(PostRaw).where(
                PostRaw.source == "reddit",
                PostRaw.source_post_id == test_post_id,
            )
        )
        cold_row = result.scalar_one_or_none()

        if cold_row:
            print(f"✅ 冷库验证成功:")
            print(f"   - ID: {cold_row.id}")
            print(f"   - Source: {cold_row.source}")
            print(f"   - Post ID: {cold_row.source_post_id}")
            print(f"   - Version: {cold_row.version}")
            print(f"   - Title: {cold_row.title}")
            print(f"   - Subreddit: {cold_row.subreddit}")
            print(f"   - Score: {cold_row.score}")
            print(f"   - Comments: {cold_row.num_comments}")
            print(f"   - Is Current: {cold_row.is_current}")
            print(f"   - Created At: {cold_row.created_at}")
            print(f"   - Fetched At: {cold_row.fetched_at}")
        else:
            print("❌ 冷库验证失败：未找到数据")
        print()

        # 5. 写入热缓存 (posts_hot)
        print("=" * 60)
        print("2️⃣  写入热缓存 (posts_hot)")
        print("=" * 60)

        from datetime import timedelta

        hot_post = PostHot(
            source="reddit",
            source_post_id=test_post_id,
            created_at=test_created_at,
            cached_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            title=test_title,
            body=test_body,
            subreddit=test_subreddit,
            score=100,
            num_comments=50,
        )

        session.add(hot_post)
        await session.commit()
        print("✅ 热缓存写入成功")
        print()

        # 6. 验证热缓存写入
        result = await session.execute(
            select(PostHot).where(
                PostHot.source == "reddit",
                PostHot.source_post_id == test_post_id,
            )
        )
        hot_row = result.scalar_one_or_none()

        if hot_row:
            print(f"✅ 热缓存验证成功:")
            print(f"   - Source: {hot_row.source}")
            print(f"   - Post ID: {hot_row.source_post_id}")
            print(f"   - Title: {hot_row.title}")
            print(f"   - Subreddit: {hot_row.subreddit}")
            print(f"   - Score: {hot_row.score}")
            print(f"   - Comments: {hot_row.num_comments}")
            print(f"   - Created At: {hot_row.created_at}")
            print(f"   - Cached At: {hot_row.cached_at}")
            print(f"   - Expires At: {hot_row.expires_at}")
        else:
            print("❌ 热缓存验证失败：未找到数据")
        print()

        # 7. 测试更新（Upsert）
        print("=" * 60)
        print("3️⃣  测试 Upsert 功能")
        print("=" * 60)

        # 更新冷库（增加 score 和 num_comments）
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = (
            pg_insert(PostRaw)
            .values(
                source="reddit",
                source_post_id=test_post_id,
                version=1,
                created_at=test_created_at,
                fetched_at=datetime.now(timezone.utc),
                title=test_title,
                body=test_body,
                subreddit=test_subreddit,
                score=150,  # 更新
                num_comments=75,  # 更新
                author_id="test_author_001",
                author_name="test_author",
            )
            .on_conflict_do_update(
                index_elements=["source", "source_post_id", "version"],
                set_={
                    "score": 150,
                    "num_comments": 75,
                    "fetched_at": datetime.now(timezone.utc),
                },
            )
        )

        await session.execute(stmt)
        await session.commit()
        print("✅ 冷库 Upsert 成功")

        # 验证更新
        result = await session.execute(
            select(PostRaw).where(
                PostRaw.source == "reddit",
                PostRaw.source_post_id == test_post_id,
            )
        )
        updated_cold = result.scalar_one_or_none()

        if updated_cold:
            print(f"✅ 冷库更新验证:")
            print(f"   - Score: {updated_cold.score} (应该是 150)")
            print(f"   - Comments: {updated_cold.num_comments} (应该是 75)")
        print()

        # 8. 统计数据
        print("=" * 60)
        print("4️⃣  统计数据")
        print("=" * 60)

        # 冷库统计
        result = await session.execute(text("SELECT COUNT(*) FROM posts_raw"))
        cold_count = result.scalar()
        print(f"📊 冷库 (posts_raw) 总数: {cold_count}")

        # 热缓存统计
        result = await session.execute(text("SELECT COUNT(*) FROM posts_hot"))
        hot_count = result.scalar()
        print(f"📊 热缓存 (posts_hot) 总数: {hot_count}")
        print()

        # 9. 清理测试数据
        print("=" * 60)
        print("5️⃣  清理测试数据")
        print("=" * 60)

        await session.execute(
            text(
                "DELETE FROM posts_raw WHERE source = 'reddit' AND source_post_id = :post_id"
            ),
            {"post_id": test_post_id},
        )
        await session.execute(
            text(
                "DELETE FROM posts_hot WHERE source = 'reddit' AND source_post_id = :post_id"
            ),
            {"post_id": test_post_id},
        )
        await session.commit()
        print("✅ 测试数据清理完成")
        print()

        print("=" * 60)
        print("🎉 冷热双写功能测试完成！")
        print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_cold_hot_dual_write())
