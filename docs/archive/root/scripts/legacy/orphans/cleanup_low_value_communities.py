#!/usr/bin/env python3
"""清理低价值社区脚本"""
import asyncio
import csv
from sqlalchemy import text
from app.db.session import SessionFactory


async def cleanup_communities():
    """清理47个低价值社区（<50帖子）"""
    
    # 1. 读取待清理社区列表
    low_value_communities = []
    with open('../待清理社区列表_47个.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('社区名称') and not row['社区名称'].startswith('说明'):
                low_value_communities.append(row['社区名称'])
    
    print(f'📋 待清理社区数量：{len(low_value_communities)}')
    print()
    
    async with SessionFactory() as db:
        # 2. 备份数据（标记为inactive，不删除）
        print('🔄 开始标记低价值社区为inactive...')
        for community in low_value_communities:
            result = await db.execute(text('''
                UPDATE community_pool
                SET is_active = false,
                    updated_at = NOW()
                WHERE name = :name
                RETURNING id, name
            '''), {'name': community})
            row = result.fetchone()
            if row:
                print(f'  ✅ {row[1]} 已标记为inactive')
            else:
                print(f'  ⚠️ {community} 不存在于community_pool')
        
        await db.commit()
        print()
        
        # 3. 验证清理结果
        print('📊 验证清理结果：')
        result = await db.execute(text('''
            SELECT 
                COUNT(*) FILTER (WHERE is_active = true) as active_count,
                COUNT(*) FILTER (WHERE is_active = false) as inactive_count,
                COUNT(*) as total_count
            FROM community_pool
        '''))
        row = result.fetchone()
        print(f'  活跃社区数：{row[0]}')
        print(f'  停用社区数：{row[1]}')
        print(f'  总社区数：{row[2]}')
        print()
        
        # 4. 统计各级别社区数量
        print('📊 社区分级统计：')
        result = await db.execute(text('''
            WITH community_stats AS (
                SELECT 
                    cp.name,
                    COUNT(pr.id) as post_count
                FROM community_pool cp
                LEFT JOIN posts_raw pr ON cp.name = pr.subreddit AND pr.is_current = true
                WHERE cp.is_active = true
                GROUP BY cp.name
            )
            SELECT 
                CASE 
                    WHEN post_count >= 1000 THEN '高价值（1000+）'
                    WHEN post_count >= 500 THEN '次高价值（500-999）'
                    WHEN post_count >= 100 THEN '扩展语义（100-499）'
                    WHEN post_count >= 50 THEN '低活跃（50-99）'
                    ELSE '极低活跃（<50）'
                END as tier,
                COUNT(*) as community_count,
                SUM(post_count) as total_posts
            FROM community_stats
            GROUP BY tier
            ORDER BY MIN(post_count) DESC
        '''))
        rows = result.fetchall()
        for row in rows:
            print(f'  {row[0]}: {row[1]}个社区，{row[2]:,}个帖子')
        print()
        
        # 5. 生成清理报告
        print('📝 生成清理报告...')
        report = []
        report.append('=' * 80)
        report.append('社区池清理报告')
        report.append('=' * 80)
        report.append('')
        report.append(f'清理时间：{asyncio.get_event_loop().time()}')
        report.append(f'清理社区数：{len(low_value_communities)}')
        report.append('')
        report.append('清理的社区列表：')
        for i, community in enumerate(low_value_communities, 1):
            report.append(f'{i}. {community}')
        report.append('')
        report.append('清理后社区池统计：')
        report.append(f'  活跃社区数：{row[0]}')
        report.append(f'  停用社区数：{row[1]}')
        report.append(f'  总社区数：{row[2]}')
        report.append('')
        report.append('=' * 80)
        
        with open('../reports/community_cleanup_report.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print('✅ 清理报告已保存到：reports/community_cleanup_report.txt')
        print()
        
        # 6. 生成新的社区池配置文件
        print('📝 生成新的社区池配置文件...')
        result = await db.execute(text('''
            WITH community_stats AS (
                SELECT 
                    cp.name,
                    cp.tier,
                    cp.priority,
                    cp.categories,
                    COUNT(pr.id) as post_count
                FROM community_pool cp
                LEFT JOIN posts_raw pr ON cp.name = pr.subreddit AND pr.is_current = true
                WHERE cp.is_active = true
                GROUP BY cp.name, cp.tier, cp.priority, cp.categories
            )
            SELECT 
                name,
                tier,
                priority,
                categories,
                post_count,
                CASE 
                    WHEN post_count >= 1000 THEN 'high'
                    WHEN post_count >= 500 THEN 'medium'
                    WHEN post_count >= 100 THEN 'low'
                    ELSE 'very_low'
                END as new_tier
            FROM community_stats
            ORDER BY post_count DESC
        '''))
        rows = result.fetchall()
        
        with open('../active_communities_176.csv', 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['社区名称', '原Tier', '原优先级', '分类', '帖子数', '新Tier'])
            for row in rows:
                writer.writerow([
                    row[0],  # name
                    row[1],  # tier
                    row[2],  # priority
                    row[3],  # categories
                    row[4],  # post_count
                    row[5],  # new_tier
                ])
        
        print('✅ 新的社区池配置已保存到：active_communities_176.csv')
        print()
        
        print('🎉 清理完成！')
        print()
        print('下一步：')
        print('1. 验证社区池统计：make pool-stats')
        print('2. 更新抓取配置：backend/config/crawler.yml')
        print('3. 重启Celery服务：make dev-celery-beat')


if __name__ == '__main__':
    asyncio.run(cleanup_communities())

