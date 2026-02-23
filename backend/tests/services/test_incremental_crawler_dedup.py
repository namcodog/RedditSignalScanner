"""
测试增量抓取器去重逻辑

验收标准:
1. 准确识别新增帖子 (is_new=True)
2. 准确识别重复帖子 (duplicates)
3. 准确识别更新帖子 (is_updated=True)
4. 统计数量一致性: new_posts + updated_posts + duplicates = total
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
import uuid
from sqlalchemy import select, text

from app.services.incremental_crawler import IncrementalCrawler
from app.services.reddit_client import RedditPost
from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.models.posts_storage import PostHot, PostRaw


class TestIncrementalCrawlerDedup:
    """测试增量抓取器去重逻辑"""

    @pytest_asyncio.fixture
    async def db_session(self):
        """创建测试用的数据库 session"""
        async with SessionFactory() as db:
            yield db

    @pytest_asyncio.fixture(autouse=True)
    async def _reset_tables(self, db_session) -> None:
        await db_session.execute(
            text(
                "TRUNCATE TABLE community_cache, community_pool, posts_raw, posts_hot RESTART IDENTITY CASCADE"
            )
        )
        await db_session.commit()

    @pytest_asyncio.fixture
    async def crawler(self, db_session) -> IncrementalCrawler:
        """创建测试用的 IncrementalCrawler 实例"""
        reddit_client = AsyncMock()
        crawler = IncrementalCrawler(
            db=db_session,
            reddit_client=reddit_client,
            hot_cache_ttl_hours=24,
            spam_filter_mode="allow",
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

    async def _ensure_pool(self, db_session, community_name: str) -> None:
        existing = (
            await db_session.execute(
                select(CommunityPool).where(CommunityPool.name == community_name)
            )
        ).scalar_one_or_none()
        if existing:
            return
        pool = CommunityPool(
            name=community_name,
            tier="medium",
            categories={"topic": ["test"]},
            description_keywords={"test": 1},
            daily_posts=1,
            quality_score=Decimal("0.50"),
            priority="medium",
        )
        db_session.add(pool)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_new_post_detection(
        self,
        crawler: IncrementalCrawler,
        db_session,
    ) -> None:
        """验收: 准确识别新增帖子"""
        await self._ensure_pool(db_session, "r/test_new")
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
    async def test_duplicate_detection(
        self,
        crawler: IncrementalCrawler,
        db_session,
    ) -> None:
        """验收: 准确识别重复帖子"""
        await self._ensure_pool(db_session, "r/test_dup")
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
    async def test_content_hash_dedup(
        self,
        crawler: IncrementalCrawler,
        db_session,
    ) -> None:
        """验收: 内容哈希去重（不同ID但内容相同）"""
        await self._ensure_pool(db_session, "r/test_hash")
        now = datetime.now(timezone.utc).timestamp()
        post_a = self._create_mock_post(post_id="hash-a", title="Same Content", created_utc=now)
        post_b = self._create_mock_post(
            post_id="hash-b",
            title="Same Content",
            created_utc=now + 1,
        )

        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=[post_a])
        await crawler.crawl_community_incremental("r/test_hash", limit=1)

        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=[post_b])
        result = await crawler.crawl_community_incremental("r/test_hash", limit=1)

        assert result["new_posts"] == 0
        assert result["duplicates"] == 1
        assert result["updated_posts"] == 0

        result_db = await db_session.execute(
            select(PostRaw).where(PostRaw.source_post_id.in_([post_a.id, post_b.id]))
        )
        records = list(result_db.scalars())
        assert len(records) == 2
        metadata = {record.source_post_id: record.extra_data for record in records}
        assert metadata[post_b.id]["duplicate_of"] == post_a.id
        assert metadata[post_b.id]["is_duplicate"] is True
        assert metadata[post_a.id].get("is_duplicate") is not True

    @pytest.mark.asyncio
    async def test_spam_tag_mode_keeps_post(
        self,
        db_session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """验收: spam tag 模式会保留帖子并打标"""
        await self._ensure_pool(db_session, "r/test_spam_tag")
        reddit_client = AsyncMock()
        crawler = IncrementalCrawler(
            db=db_session,
            reddit_client=reddit_client,
            hot_cache_ttl_hours=24,
            spam_filter_mode="tag",
        )
        post = RedditPost(
            id="spam-tag-1",
            title="Spam Tag Post",
            selftext="Spam body",
            score=1,
            num_comments=1,
            created_utc=datetime.now(timezone.utc).timestamp(),
            subreddit="r/test_spam_tag",
            author="test_author",
            url="https://reddit.com/r/test_spam_tag/comments/spam-tag-1",
            permalink="/r/test_spam_tag/comments/spam-tag-1",
        )
        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=[post])
        monkeypatch.setattr(crawler, "_is_spam_post", lambda _p: "Spam_Ad")

        result = await crawler.crawl_community_incremental("r/test_spam_tag", limit=1)

        assert result["new_posts"] == 1
        assert result["duplicates"] == 0

        record = (
            await db_session.execute(
                select(PostRaw).where(PostRaw.source_post_id == post.id)
            )
        ).scalar_one()
        assert record.extra_data.get("spam_category") == "Spam_Ad"

    @pytest.mark.asyncio
    async def test_comments_backfill_enqueues_for_new_posts(
        self,
        db_session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """验收: 增量回填评论只对新增帖子触发且受上限控制"""
        await self._ensure_pool(db_session, "r/test_comments")
        reddit_client = AsyncMock()
        crawler = IncrementalCrawler(
            db=db_session,
            reddit_client=reddit_client,
            hot_cache_ttl_hours=24,
            enable_comments_backfill=True,
            comments_backfill_max_posts=2,
            comments_backfill_limit=5,
            comments_backfill_depth=1,
            spam_filter_mode="allow",
        )

        posts = [
            self._create_mock_post(post_id="c1", title="C1"),
            self._create_mock_post(post_id="c2", title="C2"),
            self._create_mock_post(post_id="c3", title="C3"),
        ]
        posts[0].num_comments = 10
        posts[1].num_comments = 3
        posts[2].num_comments = 7

        reddit_client.fetch_subreddit_posts = AsyncMock(return_value=posts)
        scheduled: list[tuple[str, dict[str, Any]]] = []

        def fake_send_task(task_name: str, *args, **kwargs) -> None:
            scheduled.append((task_name, kwargs))

        monkeypatch.setattr("app.core.celery_app.celery_app.send_task", fake_send_task)

        await crawler.crawl_community_incremental("r/test_comments", limit=3)

        comment_tasks = [
            item for item in scheduled if item[0] == "comments.fetch_and_ingest"
        ]
        assert len(comment_tasks) == 2
        comment_ids = {
            task[1]["kwargs"]["source_post_id"] for task in comment_tasks
        }
        assert comment_ids == {"c1", "c3"}

    @pytest.mark.asyncio
    async def test_update_detection(
        self,
        crawler: IncrementalCrawler,
        db_session,
    ) -> None:
        """验收: 准确识别更新帖子（score/comments 变化）"""
        await self._ensure_pool(db_session, "r/test_update")
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
    async def test_statistics_consistency(
        self,
        crawler: IncrementalCrawler,
        db_session,
    ) -> None:
        """验收: 统计数量一致性"""
        await self._ensure_pool(db_session, "r/test_mixed")
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
    async def test_hot_cache_persists_author_metadata(
        self,
        crawler: IncrementalCrawler,
        db_session,
    ) -> None:
        """验收: 热缓存记录保存作者信息"""
        subreddit = "r/test_hot_author"
        await self._ensure_pool(db_session, subreddit)
        post = self._create_mock_post(post_id="hot-author-1", title="Hot Author Post")

        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=[post])
        await crawler.crawl_community_incremental(subreddit, limit=1)

        result = await db_session.execute(
            select(PostHot).where(PostHot.source_post_id == post.id)
        )
        record = result.scalar_one()

        assert record.author_id == post.author
        assert record.author_name == post.author

    @pytest.mark.asyncio
    async def test_dual_write_triggers_refresh_on_changes(
        self,
        crawler: IncrementalCrawler,
        db_session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """验收: 新增数据后会异步触发物化视图刷新"""
        await self._ensure_pool(db_session, "r/test_refresh")
        scheduled: list[str] = []

        def fake_send_task(task_name: str, *args, **kwargs) -> None:
            scheduled.append(task_name)

        monkeypatch.setattr(
            "app.core.celery_app.celery_app.send_task", fake_send_task
        )

        post = self._create_mock_post(post_id="refresh-trigger", title="Trigger Refresh")
        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=[post])

        await crawler.crawl_community_incremental("r/test_refresh", limit=1)

        assert "tasks.maintenance.refresh_posts_latest" in scheduled

    @pytest.mark.asyncio
    async def test_scd2_creates_new_version_and_expires_previous(
        self,
        crawler: IncrementalCrawler,
        db_session,
    ) -> None:
        """验收: 更新时生成新版本并正确关闭旧版本"""
        subreddit = "r/test_scd2"
        await self._ensure_pool(db_session, subreddit)
        post_id = str(uuid.uuid4())[:8]

        # 第一次抓取: 新增版本1
        initial_post = self._create_mock_post(post_id=post_id, title="SCD2 Post", score=3)
        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=[initial_post])
        await crawler.crawl_community_incremental(subreddit, limit=1)

        # 第二次抓取: 分数变化 -> 应触发新版本
        updated_post = self._create_mock_post(post_id=post_id, title="SCD2 Post", score=10)
        crawler.reddit_client.fetch_subreddit_posts = AsyncMock(return_value=[updated_post])
        await crawler.crawl_community_incremental(subreddit, limit=1)

        # 查询所有版本
        result = await db_session.execute(
            select(PostRaw)
            .where(PostRaw.source == "reddit", PostRaw.source_post_id == post_id)
            .order_by(PostRaw.version.asc())
        )
        versions = list(result.scalars())

        assert len(versions) == 2, "应存在两个版本记录"
        v1, v2 = versions

        # 版本1应已失效
        assert v1.version == 1
        assert v1.is_current is False
        assert v1.valid_to is not None
        assert v1.valid_to.year != 9999

        # 版本2应为当前版本且分数更新
        assert v2.version == 2
        assert v2.is_current is True
        assert v2.score == 10
        assert v2.valid_from >= v1.valid_to

    @pytest.mark.asyncio
    async def test_watermark_filtering(
        self,
        crawler: IncrementalCrawler,
        db_session,
    ) -> None:
        """验收: 水位线过滤旧帖子"""
        await self._ensure_pool(db_session, "r/test_watermark")
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
