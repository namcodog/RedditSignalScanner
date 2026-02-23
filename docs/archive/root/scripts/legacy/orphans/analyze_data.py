#!/usr/bin/env python3
"""数据分析脚本"""
import asyncio
from sqlalchemy import text
from app.db.session import SessionFactory


async def analyze_data():
    async with SessionFactory() as db:
        output = []
        output.append('=' * 80)
        output.append('Reddit信号扫描器 - 数据分析报告')
        output.append('=' * 80)
        output.append('')
        
        # 1. 总体概况
        output.append('【一、总体概况】')
        output.append('-' * 80)
        result = await db.execute(text('SELECT COUNT(*) FROM posts_raw WHERE is_current = true'))
        total_posts = result.scalar()
        output.append(f'总帖子数：{total_posts:,}')
        
        result = await db.execute(text('SELECT COUNT(DISTINCT subreddit) FROM posts_raw WHERE is_current = true'))
        total_communities = result.scalar()
        output.append(f'社区数量：{total_communities}')
        
        avg_posts = total_posts / total_communities
        output.append(f'平均每社区帖子数：{avg_posts:.1f}')
        output.append('')
        
        # 2. 社区分布分析
        output.append('【二、社区帖子数分布】')
        output.append('-' * 80)
        result = await db.execute(text('''
            WITH community_stats AS (
                SELECT subreddit, COUNT(*) as post_count
                FROM posts_raw WHERE is_current = true
                GROUP BY subreddit
            )
            SELECT 
                CASE 
                    WHEN post_count >= 1000 THEN '1000+'
                    WHEN post_count >= 500 THEN '500-999'
                    WHEN post_count >= 100 THEN '100-499'
                    WHEN post_count >= 50 THEN '50-99'
                    ELSE '0-49'
                END as range,
                COUNT(*) as community_count,
                SUM(post_count) as total_posts
            FROM community_stats
            GROUP BY range
            ORDER BY MIN(post_count) DESC
        '''))
        rows = result.fetchall()
        output.append(f"{'帖子数范围':<15} {'社区数量':<10} {'总帖子数':<15} {'占比':<10}")
        output.append('-' * 60)
        for row in rows:
            percentage = (row[2] / total_posts) * 100
            output.append(f'{row[0]:<15} {row[1]:<10} {row[2]:<15,} {percentage:>6.1f}%')
        output.append('')
        
        # 3. Top 20 活跃社区
        output.append('【三、Top 20 活跃社区】')
        output.append('-' * 80)
        result = await db.execute(text('''
            SELECT subreddit, COUNT(*) as post_count,
                   COUNT(DISTINCT DATE(created_at)) as active_days
            FROM posts_raw WHERE is_current = true
            GROUP BY subreddit ORDER BY post_count DESC LIMIT 20
        '''))
        rows = result.fetchall()
        output.append(f"{'排名':<5} {'社区':<30} {'帖子数':<10} {'活跃天数':<10}")
        output.append('-' * 65)
        for i, row in enumerate(rows, 1):
            output.append(f'{i:<5} {row[0]:<30} {row[1]:<10,} {row[2]:<10}')
        output.append('')
        
        # 4. 时间分布
        output.append('【四、时间分布分析】')
        output.append('-' * 80)
        result = await db.execute(text('''
            SELECT DATE_TRUNC('year', created_at) as year, COUNT(*) as post_count
            FROM posts_raw WHERE is_current = true
            GROUP BY year ORDER BY year DESC LIMIT 10
        '''))
        rows = result.fetchall()
        output.append(f"{'年份':<15} {'帖子数':<15} {'占比':<10}")
        output.append('-' * 50)
        for row in rows:
            year = row[0].year
            percentage = (row[1] / total_posts) * 100
            output.append(f'{year:<15} {row[1]:<15,} {percentage:>6.1f}%')
        output.append('')
        
        # 5. 分数分析
        output.append('【五、帖子分数分析】')
        output.append('-' * 80)
        result = await db.execute(text('''
            SELECT MIN(score), MAX(score), AVG(score)::INTEGER,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY score)::INTEGER,
                   PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY score)::INTEGER
            FROM posts_raw WHERE is_current = true
        '''))
        row = result.fetchone()
        output.append(f'最低分数：{row[0]:,}')
        output.append(f'最高分数：{row[1]:,}')
        output.append(f'平均分数：{row[2]:,}')
        output.append(f'中位数：{row[3]:,}')
        output.append(f'90分位数：{row[4]:,}')
        output.append('')
        
        # 6. 评论数分析
        output.append('【六、评论数分析】')
        output.append('-' * 80)
        result = await db.execute(text('''
            SELECT MIN(num_comments), MAX(num_comments), AVG(num_comments)::INTEGER,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY num_comments)::INTEGER,
                   PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY num_comments)::INTEGER
            FROM posts_raw WHERE is_current = true
        '''))
        row = result.fetchone()
        output.append(f'最少评论数：{row[0]:,}')
        output.append(f'最多评论数：{row[1]:,}')
        output.append(f'平均评论数：{row[2]:,}')
        output.append(f'中位数：{row[3]:,}')
        output.append(f'90分位数：{row[4]:,}')
        output.append('')
        
        # 7. 高质量帖子
        output.append('【七、高质量帖子分析】')
        output.append('-' * 80)
        result = await db.execute(text('SELECT COUNT(*) FROM posts_raw WHERE is_current = true AND score >= 100'))
        high_score = result.scalar()
        output.append(f'高分帖子（score >= 100）：{high_score:,}（{high_score/total_posts*100:.1f}%）')
        
        result = await db.execute(text('SELECT COUNT(*) FROM posts_raw WHERE is_current = true AND num_comments >= 50'))
        high_comments = result.scalar()
        output.append(f'高评论帖子（comments >= 50）：{high_comments:,}（{high_comments/total_posts*100:.1f}%）')
        
        result = await db.execute(text('SELECT COUNT(*) FROM posts_raw WHERE is_current = true AND score >= 100 AND num_comments >= 50'))
        high_quality = result.scalar()
        output.append(f'高质量帖子（两者兼具）：{high_quality:,}（{high_quality/total_posts*100:.1f}%）')
        output.append('')
        
        # 8. 最近活跃度
        output.append('【八、最近活跃度分析】')
        output.append('-' * 80)
        result = await db.execute(text("SELECT COUNT(*) FROM posts_raw WHERE is_current = true AND created_at >= NOW() - INTERVAL '30 days'"))
        recent_30d = result.scalar()
        output.append(f'最近30天：{recent_30d:,}（{recent_30d/total_posts*100:.1f}%）')
        
        result = await db.execute(text("SELECT COUNT(*) FROM posts_raw WHERE is_current = true AND created_at >= NOW() - INTERVAL '7 days'"))
        recent_7d = result.scalar()
        output.append(f'最近7天：{recent_7d:,}（{recent_7d/total_posts*100:.1f}%）')
        
        result = await db.execute(text("SELECT COUNT(*) FROM posts_raw WHERE is_current = true AND created_at >= NOW() - INTERVAL '1 day'"))
        recent_1d = result.scalar()
        output.append(f'最近1天：{recent_1d:,}（{recent_1d/total_posts*100:.1f}%）')
        output.append('')
        
        # 9. 数据质量
        output.append('【九、数据质量总结】')
        output.append('-' * 80)
        result = await db.execute(text('''
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN title IS NOT NULL AND title != '' THEN 1 END) as has_title,
                   COUNT(CASE WHEN score > 0 THEN 1 END) as positive_score,
                   COUNT(CASE WHEN num_comments > 0 THEN 1 END) as has_comments
            FROM posts_raw WHERE is_current = true
        '''))
        row = result.fetchone()
        output.append(f'总帖子数：{row[0]:,}')
        output.append(f'有标题：{row[1]:,}（{row[1]/row[0]*100:.1f}%）')
        output.append(f'正分帖子：{row[2]:,}（{row[2]/row[0]*100:.1f}%）')
        output.append(f'有评论：{row[3]:,}（{row[3]/row[0]*100:.1f}%）')
        output.append('')
        output.append('=' * 80)
        
        # 打印到控制台
        for line in output:
            print(line)
        
        # 保存到文件
        with open('../reports/data_analysis_20251114.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(output))
        print('\n✅ 分析报告已保存到：reports/data_analysis_20251114.txt')


if __name__ == '__main__':
    asyncio.run(analyze_data())

