"""
测试增量抓取器去重逻辑

验收标准:
1. 准确识别新增帖子 (is_new=True)
2. 准确识别重复帖子 (duplicates)
3. 准确识别更新帖子 (is_updated=True)
4. 统计数量一致性: new_posts + updated_posts + duplicates = total
"""
from __future__ import annotations

import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.services.incremental_crawler import IncrementalCrawler
from app.services.reddit_client import RedditPost
from app.db.session import SessionFactory


class TestIncrementalCrawlerDedup:
    """测试增量抓取器去重逻辑"""

    @pytest_asyncio.fixture
    async def db_session(self):
        """创建测试用的数据库 session"""
        async with SessionFactory() as db:
            yield db

    @pytest_asyncio.fixture
    async def crawler(self, db_session) -> IncrementalCrawler:
        """创建测试用的 IncrementalCrawler 实例"""
        reddit_client = AsyncMock()
        crawler = IncrementalCrawler(
            db=db_session,
            reddit_client=reddit_client,
            hot_cache_ttl_hours=24,
        )
        yield crawler

    def _create_mock_post(
        self,
        post_id: str = None,
        title: str = "Test Post",
        score: int = 10,
        created_utc: float | None = None
    ) -> RedditPost:
        """创建模拟的 RedditPost 对象"""
        # 使用 UUID 确保每次测试的 post_id 唯一
        if post_id is None:
            post_id = str(uuid.uuid4())[:8]

        if created_utc is None:
            created_utc = datetime.now(timezone.utc).timestamp()

        post = MagicMock(spec=RedditPost)
        post.id = post_id
        post.title = title
        post.selftext = f"Body of {title}"
        post.author = "test_author"
        post.score = score
        post.num_comments = 5
        post.created_utc = created_utc
        post.url = f"https://reddit.com/r/test/comments/{post_id}"
        post.permalink = f"/r/test/comments/{post_id}"
        post.upvote_ratio = 0.95  # 添加 upvote_ratio 属性
        return post

    @pytest.mark.asyncio
    async def test_new_post_detection(self, crawler: IncrementalCrawler) -> None:
        """验收: 准确识别新增帖子"""
        # 准备测试数据: 10个全新帖子（使用 UUID 确保唯一性）
        mock_posts = [
            self._create_mock_post(title=f"New Post {i}")
            for i in range(10)
        ]

        # Mock reddit_client.fetch_subreddit_posts
        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=mock_posts)

        # 执行抓取
        result = await crawler.crawl_community_incremental("r/test_new", limit=10)

        # 验收: 所有帖子都是新增
        assert result["new_posts"] == 10
        assert result["updated_posts"] == 0
        assert result["duplicates"] == 0
        assert result["watermark_updated"] is True

    @pytest.mark.asyncio
    async def test_duplicate_detection(self, crawler: IncrementalCrawler) -> None:
        """验收: 准确识别重复帖子"""
        # 生成唯一的 post_id 列表（用于两次抓取）
        post_ids = [str(uuid.uuid4())[:8] for _ in range(10)]

        # 第一次抓取的时间戳
        now = datetime.now(timezone.utc).timestamp()

        # 准备测试数据
        mock_posts = [
            self._create_mock_post(post_id=post_ids[i], title=f"Duplicate Post {i}", created_utc=now)
            for i in range(10)
        ]

        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=mock_posts)

        # 第一次抓取: 全部新增
        result1 = await crawler.crawl_community_incremental("r/test_dup", limit=10)
        assert result1["new_posts"] == 10
        assert result1["duplicates"] == 0

        # 第二次抓取: 相同数据，但时间戳稍微更新（绕过水位线过滤）
        now_updated = now + 1  # 1秒后
        mock_posts_dup = [
            self._create_mock_post(post_id=post_ids[i], title=f"Duplicate Post {i}", created_utc=now_updated)
            for i in range(10)
        ]
        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=mock_posts_dup)

        result2 = await crawler.crawl_community_incremental("r/test_dup", limit=10)

        # 验收: 所有帖子都是重复
        assert result2["new_posts"] == 0
        assert result2["duplicates"] == 10
        assert result2["updated_posts"] == 0

    @pytest.mark.asyncio
    async def test_update_detection(self, crawler: IncrementalCrawler) -> None:
        """验收: 准确识别更新帖子（score/comments 变化）"""
        # 生成唯一的 post_id 列表（用于两次抓取）
        post_ids = [str(uuid.uuid4())[:8] for _ in range(10)]

        # 准备测试数据
        mock_posts_v1 = [
            self._create_mock_post(post_id=post_ids[i], title=f"Update Post {i}", score=10)
            for i in range(10)
        ]

        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=mock_posts_v1)

        # 第一次抓取
        result1 = await crawler.crawl_community_incremental("r/test_update", limit=10)
        assert result1["new_posts"] == 10

        # 模拟帖子获得更多点赞（score 变化）
        mock_posts_v2 = [
            self._create_mock_post(post_id=post_ids[i], title=f"Update Post {i}", score=100)
            for i in range(10)
        ]

        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=mock_posts_v2)

        # 第二次抓取
        result2 = await crawler.crawl_community_incremental("r/test_update", limit=10)
        
        # 验收: 检测到更新
        assert result2["updated_posts"] > 0
        assert result2["new_posts"] == 0

    @pytest.mark.asyncio
    async def test_statistics_consistency(self, crawler: IncrementalCrawler) -> None:
        """验收: 统计数量一致性"""
        # 准备混合数据: 5个新帖子 + 5个重复帖子
        # 先插入5个帖子
        initial_posts = [
            self._create_mock_post(f"mixed_post_{i}", f"Mixed Post {i}")
            for i in range(5)
        ]
        
        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=initial_posts)
        await crawler.crawl_community_incremental("r/test_mixed", limit=5)
        
        # 再抓取10个帖子（前5个重复，后5个新增）
        mixed_posts = [
            self._create_mock_post(f"mixed_post_{i}", f"Mixed Post {i}")
            for i in range(10)
        ]
        
        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=mixed_posts)
        result = await crawler.crawl_community_incremental("r/test_mixed", limit=10)
        
        # 验收: 统计一致性
        total = result["new_posts"] + result["updated_posts"] + result["duplicates"]
        assert total == 10  # 应该等于抓取的总数

    @pytest.mark.asyncio
    async def test_watermark_filtering(self, crawler: IncrementalCrawler) -> None:
        """验收: 水位线过滤旧帖子"""
        # 准备测试数据: 5个旧帖子 + 5个新帖子
        now = datetime.now(timezone.utc).timestamp()
        old_time = now - 86400 * 7  # 7天前

        # 生成唯一的 post_id
        old_post_ids = [str(uuid.uuid4())[:8] for _ in range(5)]
        new_post_ids = [str(uuid.uuid4())[:8] for _ in range(5)]

        old_posts = [
            self._create_mock_post(post_id=old_post_ids[i], title=f"Old Post {i}", created_utc=old_time)
            for i in range(5)
        ]

        new_posts = [
            self._create_mock_post(post_id=new_post_ids[i], title=f"New Post {i}", created_utc=now)
            for i in range(5)
        ]

        # 第一次抓取: 插入旧帖子
        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=old_posts)
        await crawler.crawl_community_incremental("r/test_watermark", limit=5)

        # 第二次抓取: 混合旧帖子和新帖子
        mixed_posts = old_posts + new_posts
        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=mixed_posts)
        result = await crawler.crawl_community_incremental("r/test_watermark", limit=10)
        
        # 验收: 只处理新帖子（水位线之后）
        assert result["new_posts"] == 5  # 只有5个新帖子
        # 旧帖子应该被水位线过滤掉，不计入 duplicates

