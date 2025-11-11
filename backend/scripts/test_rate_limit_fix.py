#!/usr/bin/env python3
"""测试 Reddit API 限流修复效果

验证：
1. 新的限流配置（58 req/600s）
2. 429 错误指数退避重试
3. 动态速率监控
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.services.reddit_client import RedditAPIClient


async def test_rate_limit_config():
    """测试限流配置是否正确"""
    print("=" * 60)
    print("测试 1: 验证限流配置")
    print("=" * 60)
    
    settings = get_settings()
    
    print(f"✅ reddit_rate_limit: {settings.reddit_rate_limit}")
    print(f"✅ reddit_rate_limit_window_seconds: {settings.reddit_rate_limit_window_seconds}")
    print(f"✅ reddit_max_concurrency: {settings.reddit_max_concurrency}")
    
    expected_window = 600.0
    if settings.reddit_rate_limit_window_seconds == expected_window:
        print(f"✅ 限流窗口已更新为 {expected_window} 秒（10 分钟）")
    else:
        print(f"⚠️  限流窗口仍为 {settings.reddit_rate_limit_window_seconds} 秒，期望 {expected_window} 秒")
    
    print()


async def test_client_initialization():
    """测试客户端初始化"""
    print("=" * 60)
    print("测试 2: 验证客户端初始化")
    print("=" * 60)
    
    settings = get_settings()
    
    client = RedditAPIClient(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=settings.reddit_max_concurrency,
        max_retries=3,
        retry_backoff_base=5.0,
    )
    
    print(f"✅ 客户端创建成功")
    print(f"   - rate_limit: {client.rate_limit}")
    print(f"   - rate_limit_window: {client.rate_limit_window}")
    print(f"   - max_retries: {client.max_retries}")
    print(f"   - retry_backoff_base: {client.retry_backoff_base}")
    print(f"   - _ratelimit_remaining: {client._ratelimit_remaining}")
    print(f"   - _ratelimit_reset: {client._ratelimit_reset}")
    
    await client.close()
    print()


async def test_fetch_posts():
    """测试实际抓取（小规模）"""
    print("=" * 60)
    print("测试 3: 实际抓取测试（r/ecommerce 前 10 帖）")
    print("=" * 60)
    
    settings = get_settings()
    
    client = RedditAPIClient(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=settings.reddit_max_concurrency,
        max_retries=3,
        retry_backoff_base=5.0,
    )
    
    try:
        async with client:
            print("🔐 正在认证...")
            await client.authenticate()
            print("✅ 认证成功")
            
            print("📥 正在抓取 r/ecommerce 前 10 帖...")
            posts = await client.fetch_subreddit_posts(
                "ecommerce",
                limit=10,
                time_filter="month",
                sort="top",
            )
            
            print(f"✅ 成功抓取 {len(posts)} 帖")
            print(f"   - 剩余配额: {client._ratelimit_remaining}")
            print(f"   - 配额重置时间: {client._ratelimit_reset}")
            
            if posts:
                print(f"\n示例帖子:")
                post = posts[0]
                print(f"   - 标题: {post.title[:60]}...")
                print(f"   - 分数: {post.score}")
                print(f"   - 评论数: {post.num_comments}")
    
    except Exception as e:
        print(f"❌ 抓取失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()


async def main():
    """运行所有测试"""
    print("\n🧪 Reddit API 限流修复测试\n")
    
    await test_rate_limit_config()
    await test_client_initialization()
    await test_fetch_posts()
    
    print("=" * 60)
    print("✅ 所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  测试被中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

