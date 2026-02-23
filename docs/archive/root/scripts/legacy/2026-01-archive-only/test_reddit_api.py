#!/usr/bin/env python3
"""
快速测试 Reddit API 是否正常工作

用途：验证 Reddit API 配置和抓取功能
执行：python scripts/test_reddit_api.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.services.reddit_client import RedditAPIClient


async def test_reddit_api():
    """测试 Reddit API 连接和抓取功能"""
    print("=" * 80)
    print("🧪 测试 Reddit API")
    print("=" * 80)
    print()

    # 1. 检查配置
    settings = get_settings()
    print("📋 配置检查:")
    print(f"   CLIENT_ID: {'✅ 已配置' if settings.reddit_client_id else '❌ 未配置'}")
    print(f"   CLIENT_SECRET: {'✅ 已配置' if settings.reddit_client_secret else '❌ 未配置'}")
    print(f"   USER_AGENT: {settings.reddit_user_agent}")
    print()

    if not settings.reddit_client_id or not settings.reddit_client_secret:
        print("❌ Reddit API 未配置，请设置环境变量：")
        print("   REDDIT_CLIENT_ID")
        print("   REDDIT_CLIENT_SECRET")
        return False

    # 2. 测试 API 连接
    print("🔌 测试 API 连接...")
    try:
        client = RedditAPIClient(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        )
        print("✅ Reddit 客户端创建成功")
    except Exception as e:
        print(f"❌ 创建客户端失败: {e}")
        return False

    # 3. 测试抓取帖子（使用一个流行的测试社区）
    print()
    print("📥 测试抓取帖子（从 r/python 抓取 5 条）...")
    try:
        posts = await client.fetch_subreddit_posts(
            subreddit="python",
            limit=5,
            time_filter="week",
        )
        
        if not posts:
            print("⚠️  未抓取到帖子（可能是 API 限流或社区无新帖）")
            return False
        
        print(f"✅ 成功抓取 {len(posts)} 条帖子")
        print()
        print("📋 示例帖子:")
        for i, post in enumerate(posts[:3], 1):
            print(f"\n   {i}. {post.title[:60]}...")
            print(f"      - Score: {post.score}")
            print(f"      - Comments: {post.num_comments}")
            print(f"      - Subreddit: r/{post.subreddit}")
        
        return True
        
    except Exception as e:
        print(f"❌ 抓取失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    success = await test_reddit_api()
    
    print()
    print("=" * 80)
    if success:
        print("✅ Reddit API 测试通过！")
        print()
        print("🚀 下一步:")
        print("   1. 启动后台抓取: make warmup-start")
        print("   2. 监控进度: make warmup-logs")
        print("   3. 查看状态: make warmup-status")
    else:
        print("❌ Reddit API 测试失败")
        print()
        print("🔧 排查步骤:")
        print("   1. 检查环境变量配置")
        print("   2. 验证 Reddit API credentials")
        print("   3. 检查网络连接")
    print("=" * 80)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

