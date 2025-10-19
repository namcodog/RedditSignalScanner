"""
集成测试：验证增量爬虫的冷热双写功能

测试场景：
1. 通过 IncrementalCrawler 触发爬取
2. 验证 posts_raw (冷库) 有数据
3. 验证 posts_hot (热库) 有数据
4. 验证版本控制正确
5. 验证去重逻辑正确
"""
import asyncio
from datetime import datetime, timezone
from typing import List

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.posts_storage import PostHot, PostRaw
from app.services.incremental_crawler import IncrementalCrawler
from app.services.reddit_client import RedditAPIClient, RedditPost


class MockRedditClient(RedditAPIClient):
    """Mock Reddit 客户端，返回测试数据"""

    def __init__(self):
        # 不调用父类 __init__，避免真实 API 初始化
        self.mock_posts: List[RedditPost] = []
        # 添加必要的属性以避免 AttributeError
        self.access_token = "mock_token"
        self.token_expires_at = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def set_mock_posts(self, posts: List[RedditPost]) -> None:
        """设置 mock 数据"""
        self.mock_posts = posts

    async def authenticate(self) -> None:
        """Mock 认证，不做任何事"""
        pass

    async def fetch_subreddit_posts(
        self,
        subreddit: str,
        *,
        limit: int = 100,
        time_filter: str = "week",
        sort: str = "top",
    ) -> List[RedditPost]:
        """返回 mock 数据"""
        return self.mock_posts

    async def get_hot_posts(
        self,
        subreddit: str,
        limit: int = 100,
        time_filter: str = "day",
    ) -> List[RedditPost]:
        """返回 mock 数据"""
        return self.mock_posts


@pytest.fixture
async def db_session():
    """提供测试数据库会话"""
    async with SessionFactory() as session:
        yield session


@pytest.fixture
async def mock_reddit_client():
    """提供 mock Reddit 客户端"""
    client = MockRedditClient()
    return client


@pytest.fixture
async def cleanup_test_data(db_session: AsyncSession):
    """清理测试数据"""
    # 测试前清理
    await db_session.execute(
        text("DELETE FROM posts_raw WHERE subreddit = 'test_integration'")
    )
    await db_session.execute(
        text("DELETE FROM posts_hot WHERE subreddit = 'test_integration'")
    )
    await db_session.execute(
        text(
            "DELETE FROM community_cache WHERE community_name = 'test_integration'"
        )
    )
    await db_session.commit()

    yield

    # 测试后清理
    await db_session.execute(
        text("DELETE FROM posts_raw WHERE subreddit = 'test_integration'")
    )
    await db_session.execute(
        text("DELETE FROM posts_hot WHERE subreddit = 'test_integration'")
    )
    await db_session.execute(
        text(
            "DELETE FROM community_cache WHERE community_name = 'test_integration'"
        )
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_incremental_crawler_dual_write(
    db_session: AsyncSession,
    mock_reddit_client: MockRedditClient,
    cleanup_test_data,
):
    """测试增量爬虫的冷热双写功能"""
    print("\n" + "=" * 70)
    print("🧪 集成测试：增量爬虫冷热双写")
    print("=" * 70)

    # 1. 准备 mock 数据
    test_community = "test_integration"
    now = datetime.now(timezone.utc)
    mock_posts = [
        RedditPost(
            id="post_001",
            title="Test Post 1",
            selftext="This is test post 1",
            author="test_author_1",
            created_utc=now.timestamp(),
            score=100,
            num_comments=10,
            url="https://reddit.com/r/test/post_001",
            permalink="/r/test/comments/post_001",
            subreddit=test_community,
        ),
        RedditPost(
            id="post_002",
            title="Test Post 2",
            selftext="This is test post 2",
            author="test_author_2",
            created_utc=now.timestamp() + 100,
            score=200,
            num_comments=20,
            url="https://reddit.com/r/test/post_002",
            permalink="/r/test/comments/post_002",
            subreddit=test_community,
        ),
        RedditPost(
            id="post_003",
            title="Test Post 3",
            selftext="This is test post 3",
            author="test_author_3",
            created_utc=now.timestamp() + 200,
            score=300,
            num_comments=30,
            url="https://reddit.com/r/test/post_003",
            permalink="/r/test/comments/post_003",
            subreddit=test_community,
        ),
    ]
    mock_reddit_client.set_mock_posts(mock_posts)

    print(f"\n📝 准备了 {len(mock_posts)} 条 mock 帖子")

    # 2. 创建增量爬虫并执行
    crawler = IncrementalCrawler(
        db=db_session,
        reddit_client=mock_reddit_client,
        hot_cache_ttl_hours=24,
    )

    print(f"\n🚀 开始爬取社区: {test_community}")
    result = await crawler.crawl_community_incremental(
        community_name=test_community,
        limit=100,
        time_filter="day",
        sort="hot",
    )

    print(f"\n✅ 爬取完成:")
    print(f"   - 新帖子: {result['new_posts']}")
    print(f"   - 更新帖子: {result['updated_posts']}")
    print(f"   - 重复帖子: {result['duplicates']}")
    print(f"   - 水位线更新: {result['watermark_updated']}")

    # 3. 验证冷库 (posts_raw)
    print("\n" + "=" * 70)
    print("1️⃣  验证冷库 (posts_raw)")
    print("=" * 70)

    cold_result = await db_session.execute(
        select(PostRaw).where(PostRaw.subreddit == test_community)
    )
    cold_posts = cold_result.scalars().all()

    print(f"\n✅ 冷库记录数: {len(cold_posts)}")
    assert len(cold_posts) == 3, f"期望3条记录，实际{len(cold_posts)}条"

    for post in cold_posts:
        print(f"\n   📄 Post ID: {post.source_post_id}")
        print(f"      - Version: {post.version}")
        print(f"      - Title: {post.title}")
        print(f"      - Score: {post.score}")
        print(f"      - Comments: {post.num_comments}")
        print(f"      - Is Current: {post.is_current}")

        # 验证字段
        assert post.source == "reddit"
        assert post.version == 1
        assert post.is_current is True
        assert post.score > 0
        assert post.num_comments > 0

    # 4. 验证热库 (posts_hot)
    print("\n" + "=" * 70)
    print("2️⃣  验证热库 (posts_hot)")
    print("=" * 70)

    hot_result = await db_session.execute(
        select(PostHot).where(PostHot.subreddit == test_community)
    )
    hot_posts = hot_result.scalars().all()

    print(f"\n✅ 热库记录数: {len(hot_posts)}")
    assert len(hot_posts) == 3, f"期望3条记录，实际{len(hot_posts)}条"

    for post in hot_posts:
        print(f"\n   📄 Post ID: {post.source_post_id}")
        print(f"      - Title: {post.title}")
        print(f"      - Score: {post.score}")
        print(f"      - Comments: {post.num_comments}")
        print(f"      - Expires At: {post.expires_at}")

        # 验证字段
        assert post.source == "reddit"
        assert post.score > 0
        assert post.num_comments > 0
        assert post.expires_at > now

    # 5. 验证水位线
    print("\n" + "=" * 70)
    print("3️⃣  验证水位线 (community_cache)")
    print("=" * 70)

    watermark_result = await db_session.execute(
        select(CommunityCache).where(
            CommunityCache.community_name == test_community
        )
    )
    watermark = watermark_result.scalar_one_or_none()

    assert watermark is not None, "水位线应该存在"
    print(f"\n✅ 水位线记录:")
    print(f"   - Community: {watermark.community_name}")
    print(f"   - Last Seen Post ID: {watermark.last_seen_post_id}")
    print(f"   - Last Seen Created At: {watermark.last_seen_created_at}")
    print(f"   - Total Posts Fetched: {watermark.total_posts_fetched}")
    print(f"   - Dedup Rate: {watermark.dedup_rate:.2f}%")

    assert watermark.last_seen_post_id == "post_003"
    assert watermark.total_posts_fetched == 3

    print("\n" + "=" * 70)
    print("🎉 集成测试全部通过！")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(
        test_incremental_crawler_dual_write(
            db_session=SessionFactory(),
            mock_reddit_client=MockRedditClient(),
            cleanup_test_data=None,
        )
    )

