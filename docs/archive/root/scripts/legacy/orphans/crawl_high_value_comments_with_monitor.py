#!/usr/bin/env python3
"""高价值社区评论全量抓取（带实时监控）

48个高价值社区，每社区50个帖子，全量评论（depth=8, limit=500）
"""
import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.services.reddit_client import RedditAPIClient
from app.db.session import SessionFactory
from app.services.comments_ingest import persist_comments


# 48个高价值社区列表（从CSV提取）
HIGH_VALUE_SUBREDDITS = [
    "AmazonWFShoppers", "FacebookAds", "EtsySellers", "Aliexpress", "AmazonFlexDrivers",
    "bigseo", "dropshipping", "amazonecho", "Legomarket", "dropship", "FulfillmentByAmazon",
    "amazonprime", "FASCAmazon", "peopleofwalmart", "AliExpressBR", "Etsy", "stickerstore",
    "digital_marketing", "amazon", "AmazonMerch", "Amazon_Influencer", "logistics",
    "AmazonSeller", "TikTokshop", "BestAliExpressFinds", "TechSEO", "AmazonFBA",
    "AmazonFBAOnlineRetail", "News_Walmart", "printondemand", "walmart_RX", "amazonemployees",
    "WalmartSellers", "WalmartCanada", "AmazonFBATips", "ecommercemarketing",
    "Dropshipping_Guide", "SpellcasterReviews", "AmazonWTF", "ShopifyeCommerce",
    "shopifyDev", "MerchByAmazon", "amazonfresh", "DropshippingTips", "AntiAmazon",
    "ShopifyAppDev", "AmazonAnswers", "fuckamazon"
]


class CrawlMonitor:
    """抓取监控器"""
    def __init__(self):
        self.start_time = time.time()
        self.total_subs = len(HIGH_VALUE_SUBREDDITS)
        self.completed_subs = 0
        self.total_posts = 0
        self.total_comments = 0
        self.failed_subs = []
        self.current_sub = ""
        
    def update_sub(self, sub: str):
        self.current_sub = sub
        
    def add_posts(self, count: int):
        self.total_posts += count
        
    def add_comments(self, count: int):
        self.total_comments += count
        
    def complete_sub(self):
        self.completed_subs += 1
        
    def add_failed_sub(self, sub: str):
        self.failed_subs.append(sub)
        
    def print_progress(self):
        elapsed = time.time() - self.start_time
        progress = (self.completed_subs / self.total_subs) * 100
        avg_comments_per_post = self.total_comments / self.total_posts if self.total_posts > 0 else 0
        
        print(f"\n{'='*80}")
        print(f"⏱️  运行时间: {elapsed/60:.1f} 分钟")
        print(f"📊 进度: {self.completed_subs}/{self.total_subs} 社区 ({progress:.1f}%)")
        print(f"📝 帖子数: {self.total_posts:,}")
        print(f"💬 评论数: {self.total_comments:,}")
        print(f"📈 平均评论/帖: {avg_comments_per_post:.1f}")
        if self.failed_subs:
            print(f"❌ 失败社区: {len(self.failed_subs)} 个 - {', '.join(self.failed_subs[:5])}")
        print(f"{'='*80}\n")
        
    def print_final_summary(self):
        elapsed = time.time() - self.start_time
        print(f"\n{'='*80}")
        print(f"🎉 抓取完成！")
        print(f"{'='*80}")
        print(f"⏱️  总耗时: {elapsed/60:.1f} 分钟 ({elapsed/3600:.2f} 小时)")
        print(f"📊 成功社区: {self.completed_subs - len(self.failed_subs)}/{self.total_subs}")
        print(f"📝 总帖子数: {self.total_posts:,}")
        print(f"💬 总评论数: {self.total_comments:,}")
        print(f"📈 平均评论/帖: {self.total_comments/self.total_posts if self.total_posts > 0 else 0:.1f}")
        print(f"⚡ 抓取速度: {self.total_comments/(elapsed/60):.1f} 评论/分钟")
        if self.failed_subs:
            print(f"\n❌ 失败社区 ({len(self.failed_subs)} 个):")
            for sub in self.failed_subs:
                print(f"   - r/{sub}")
        print(f"{'='*80}\n")


async def crawl_high_value_comments(post_limit: int = 50, lookback_days: int = 30):
    """抓取48个高价值社区的全量评论
    
    Args:
        post_limit: 每社区抓取帖子数
        lookback_days: 回溯天数
    """
    settings = get_settings()
    monitor = CrawlMonitor()
    
    print(f"\n{'='*80}")
    print(f"🎯 开始抓取48个高价值社区的全量评论")
    print(f"{'='*80}")
    print(f"📋 配置:")
    print(f"   - 社区数量: {len(HIGH_VALUE_SUBREDDITS)}")
    print(f"   - 每社区帖子数: {post_limit}")
    print(f"   - 回溯天数: {lookback_days}")
    print(f"   - 评论深度: 8 层")
    print(f"   - 评论限制: 500 条/帖")
    print(f"   - 速率限制: {settings.reddit_rate_limit} req/{settings.reddit_rate_limit_window_seconds}s")
    print(f"   - 并发数: {settings.reddit_max_concurrency}")
    print(f"{'='*80}\n")
    
    async with RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=settings.reddit_max_concurrency,
    ) as reddit:
        async with SessionFactory() as session:
            for idx, sub in enumerate(HIGH_VALUE_SUBREDDITS, 1):
                monitor.update_sub(sub)
                print(f"\n[{idx}/{len(HIGH_VALUE_SUBREDDITS)}] 🔄 正在抓取 r/{sub}...")
                
                try:
                    # 根据回溯天数选择时间过滤器
                    if lookback_days <= 1:
                        time_filter = "day"
                    elif lookback_days <= 7:
                        time_filter = "week"
                    elif lookback_days <= 30:
                        time_filter = "month"
                    else:
                        time_filter = "all"
                    
                    # 1. 抓取帖子
                    posts, _ = await reddit.fetch_subreddit_posts(
                        sub, limit=post_limit, time_filter=time_filter, sort="top"
                    )
                    monitor.add_posts(len(posts))
                    print(f"   ✅ 获取到 {len(posts)} 个帖子")
                    
                    # 2. 抓取每个帖子的全量评论
                    sub_comments = 0
                    for p_idx, p in enumerate(posts, 1):
                        try:
                            # 🔥 全量评论抓取：depth=8, limit=500, mode="full"
                            items = await reddit.fetch_post_comments(
                                p.id, sort="confidence", depth=8, limit=500, mode="full"
                            )
                            
                            if not items:
                                continue
                            
                            # 3. 持久化评论
                            await persist_comments(
                                session, source_post_id=p.id, subreddit=sub, comments=items
                            )
                            
                            monitor.add_comments(len(items))
                            sub_comments += len(items)
                            
                            # 每10个帖子打印一次进度
                            if p_idx % 10 == 0:
                                print(f"   📊 进度: {p_idx}/{len(posts)} 帖子, {sub_comments} 条评论")
                            
                        except Exception as e:
                            print(f"   ⚠️  帖子 {p.id} 失败: {e}")
                            continue
                    
                    await session.commit()
                    monitor.complete_sub()
                    print(f"   ✅ r/{sub} 完成: {len(posts)} 帖子, {sub_comments} 条评论")
                    
                    # 每5个社区打印一次总体进度
                    if idx % 5 == 0:
                        monitor.print_progress()
                    
                except Exception as e:
                    print(f"   ❌ r/{sub} 失败: {e}")
                    monitor.add_failed_sub(sub)
                    monitor.complete_sub()
                    continue
    
    # 打印最终总结
    monitor.print_final_summary()
    
    return {
        "total_subs": monitor.total_subs,
        "completed_subs": monitor.completed_subs,
        "total_posts": monitor.total_posts,
        "total_comments": monitor.total_comments,
        "failed_subs": monitor.failed_subs,
        "elapsed_minutes": (time.time() - monitor.start_time) / 60,
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="抓取48个高价值社区的全量评论")
    parser.add_argument("--posts", type=int, default=50, help="每社区抓取帖子数（默认50）")
    parser.add_argument("--days", type=int, default=30, help="回溯天数（默认30）")
    
    args = parser.parse_args()
    
    print(f"\n⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    result = asyncio.run(crawl_high_value_comments(args.posts, args.days))
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n✅ 抓取任务完成！")

