#!/usr/bin/env python3
"""监控评论回填进度"""
import asyncio
import sys
from datetime import datetime
from sqlalchemy import text
from app.db.session import SessionFactory
from app.utils.subreddit import normalize_subreddit_name


async def check_progress():
    """检查当前进度"""
    async with SessionFactory() as session:
        # 规范化高价值社区名为存储 key（去前缀+小写）
        high_value_keys = [
            normalize_subreddit_name(s).lower()
            for s in [
                'AmazonWFShoppers', 'FacebookAds', 'EtsySellers', 'Aliexpress', 'AmazonFlexDrivers',
                'bigseo', 'dropshipping', 'amazonecho', 'Legomarket', 'dropship', 'FulfillmentByAmazon',
                'amazonprime', 'FASCAmazon', 'peopleofwalmart', 'AliExpressBR', 'Etsy', 'stickerstore',
                'digital_marketing', 'amazon', 'AmazonMerch', 'Amazon_Influencer', 'logistics',
                'AmazonSeller', 'TikTokshop', 'BestAliExpressFinds', 'TechSEO', 'AmazonFBA',
                'AmazonFBAOnlineRetail', 'News_Walmart', 'printondemand', 'walmart_RX', 'amazonemployees',
                'WalmartSellers', 'WalmartCanada', 'AmazonFBATips', 'ecommercemarketing',
                'Dropshipping_Guide', 'SpellcasterReviews', 'AmazonWTF', 'ShopifyeCommerce',
                'shopifyDev', 'MerchByAmazon', 'amazonfresh', 'DropshippingTips', 'AntiAmazon',
                'ShopifyAppDev', 'AmazonAnswers', 'fuckamazon'
            ]
        ]
        # 总评论数
        r1 = await session.execute(text('SELECT COUNT(*) FROM comments'))
        total = r1.first()[0]
        
        # 48个高价值社区评论数
        r2 = await session.execute(
            text(
                '''
                SELECT COUNT(*) FROM comments
                WHERE lower(subreddit) = ANY(:subs)
                '''
            ),
            {"subs": high_value_keys},
        )
        high_value = r2.first()[0]
        
        # 按社区统计
        r3 = await session.execute(
            text(
                '''
                SELECT subreddit, COUNT(*) as cnt
                FROM comments
                WHERE lower(subreddit) = ANY(:subs)
                GROUP BY subreddit
                ORDER BY cnt DESC
                LIMIT 10
                '''
            ),
            {"subs": high_value_keys},
        )
        top_communities = r3.fetchall()
        
        print('=' * 80)
        print(f'评论回填进度报告 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        print('=' * 80)
        print(f'总评论数: {total:,}')
        print(f'48个高价值社区评论数: {high_value:,}')
        print(f'平均每社区: {high_value / 48:,.0f} 条')
        print('=' * 80)
        print('评论数最多的10个社区：')
        for sub, cnt in top_communities:
            print(f'  {sub:<30} {cnt:>10,}')
        print('=' * 80)


if __name__ == '__main__':
    asyncio.run(check_progress())
