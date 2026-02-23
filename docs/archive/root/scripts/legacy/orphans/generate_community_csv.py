#!/usr/bin/env python3
"""生成社区分级CSV文件"""
import asyncio
import csv
from sqlalchemy import text
from app.db.session import SessionFactory


async def generate_csv():
    async with SessionFactory() as db:
        # 获取所有社区的详细统计
        result = await db.execute(text('''
            WITH community_stats AS (
                SELECT 
                    subreddit,
                    COUNT(*) as total_posts,
                    COUNT(DISTINCT DATE(created_at)) as active_days,
                    MIN(created_at) as earliest_post,
                    MAX(created_at) as latest_post,
                    AVG(score)::INTEGER as avg_score,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY score)::INTEGER as median_score,
                    AVG(num_comments)::INTEGER as avg_comments,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY num_comments)::INTEGER as median_comments,
                    COUNT(CASE WHEN score >= 100 THEN 1 END) as high_score_posts,
                    COUNT(CASE WHEN num_comments >= 50 THEN 1 END) as high_comment_posts,
                    COUNT(CASE WHEN score >= 100 AND num_comments >= 50 THEN 1 END) as high_quality_posts,
                    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '12 months' THEN 1 END) as posts_last_12m,
                    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as posts_last_30d
                FROM posts_raw
                WHERE is_current = true
                GROUP BY subreddit
            )
            SELECT 
                subreddit,
                total_posts,
                active_days,
                earliest_post,
                latest_post,
                avg_score,
                median_score,
                avg_comments,
                median_comments,
                high_score_posts,
                high_comment_posts,
                high_quality_posts,
                posts_last_12m,
                posts_last_30d,
                ROUND(high_quality_posts::NUMERIC / total_posts * 100, 2) as quality_rate,
                ROUND(posts_last_30d::NUMERIC / total_posts * 100, 2) as recent_activity_rate
            FROM community_stats
            ORDER BY total_posts DESC
        '''))
        
        all_communities = result.fetchall()
        
        # 分级
        tier1 = []  # 1000+
        tier2 = []  # 500-999
        tier3 = []  # 100-499
        tier4 = []  # 50-99
        tier5 = []  # 0-49
        
        for row in all_communities:
            total_posts = row[1]
            if total_posts >= 1000:
                tier1.append(row)
            elif total_posts >= 500:
                tier2.append(row)
            elif total_posts >= 100:
                tier3.append(row)
            elif total_posts >= 50:
                tier4.append(row)
            else:
                tier5.append(row)
        
        # CSV表头
        headers = [
            '社区名称',
            '总帖子数',
            '活跃天数',
            '最早帖子时间',
            '最新帖子时间',
            '平均分数',
            '中位数分数',
            '平均评论数',
            '中位数评论数',
            '高分帖子数(≥100)',
            '高评论帖子数(≥50)',
            '高质量帖子数',
            '最近12个月帖子数',
            '最近30天帖子数',
            '高质量率(%)',
            '近期活跃度(%)'
        ]
        
        # 1. 高价值社区（1000+）
        with open('../高价值社区池_78个.csv', 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerow(['说明：这78个社区是核心数据源，建议抓取全量帖子+全量评论'])
            writer.writerow(['抓取策略：全量抓取，每15分钟增量更新'])
            writer.writerow([])
            for row in tier1:
                writer.writerow([
                    row[0],  # 社区名称
                    row[1],  # 总帖子数
                    row[2],  # 活跃天数
                    row[3],  # 最早帖子时间
                    row[4],  # 最新帖子时间
                    row[5],  # 平均分数
                    row[6],  # 中位数分数
                    row[7],  # 平均评论数
                    row[8],  # 中位数评论数
                    row[9],  # 高分帖子数
                    row[10], # 高评论帖子数
                    row[11], # 高质量帖子数
                    row[12], # 最近12个月帖子数
                    row[13], # 最近30天帖子数
                    row[14], # 高质量率
                    row[15], # 近期活跃度
                ])
        
        # 2. 次高价值社区（500-999）
        with open('../次高价值社区池_21个.csv', 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerow(['说明：这21个社区是补充数据源，建议抓取最近12个月帖子+评论'])
            writer.writerow(['抓取策略：抓取最近12个月数据，每30分钟增量更新'])
            writer.writerow([])
            for row in tier2:
                writer.writerow([
                    row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8],
                    row[9], row[10], row[11], row[12], row[13], row[14], row[15]
                ])
        
        # 3. 扩展语义社区（100-499）
        with open('../扩展语义社区池_77个.csv', 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerow(['说明：这77个社区提供语义多样性，建议保留但降低抓取频率'])
            writer.writerow(['抓取策略：抓取最近12个月数据，每2小时增量更新'])
            writer.writerow([])
            for row in tier3:
                writer.writerow([
                    row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8],
                    row[9], row[10], row[11], row[12], row[13], row[14], row[15]
                ])
        
        # 4. 待清理社区（<50）
        with open('../待清理社区列表_47个.csv', 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerow(['说明：这47个社区活跃度极低，建议从抓取池中移除'])
            writer.writerow(['处理策略：停止抓取，保留历史数据但不再更新'])
            writer.writerow([])
            for row in tier5:
                writer.writerow([
                    row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8],
                    row[9], row[10], row[11], row[12], row[13], row[14], row[15]
                ])
        
        # 5. 生成汇总报告
        with open('../社区分级汇总报告.csv', 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['社区分级汇总报告'])
            writer.writerow([])
            writer.writerow(['级别', '帖子数范围', '社区数量', '总帖子数', '占比', '抓取策略'])
            
            tier1_total = sum(row[1] for row in tier1)
            tier2_total = sum(row[1] for row in tier2)
            tier3_total = sum(row[1] for row in tier3)
            tier4_total = sum(row[1] for row in tier4)
            tier5_total = sum(row[1] for row in tier5)
            grand_total = tier1_total + tier2_total + tier3_total + tier4_total + tier5_total
            
            writer.writerow([
                '高价值社区',
                '1000+',
                len(tier1),
                tier1_total,
                f'{tier1_total/grand_total*100:.1f}%',
                '全量抓取（帖子+评论），每15分钟更新'
            ])
            writer.writerow([
                '次高价值社区',
                '500-999',
                len(tier2),
                tier2_total,
                f'{tier2_total/grand_total*100:.1f}%',
                '抓取最近12个月（帖子+评论），每30分钟更新'
            ])
            writer.writerow([
                '扩展语义社区',
                '100-499',
                len(tier3),
                tier3_total,
                f'{tier3_total/grand_total*100:.1f}%',
                '抓取最近12个月（仅帖子），每2小时更新'
            ])
            writer.writerow([
                '低活跃社区',
                '50-99',
                len(tier4),
                tier4_total,
                f'{tier4_total/grand_total*100:.1f}%',
                '待评估（暂不处理）'
            ])
            writer.writerow([
                '待清理社区',
                '0-49',
                len(tier5),
                tier5_total,
                f'{tier5_total/grand_total*100:.1f}%',
                '停止抓取，保留历史数据'
            ])
            writer.writerow([])
            writer.writerow(['总计', '', len(all_communities), grand_total, '100.0%', ''])
            writer.writerow([])
            writer.writerow(['保留社区数', f'{len(tier1) + len(tier2) + len(tier3)} 个'])
            writer.writerow(['丢弃社区数', f'{len(tier5)} 个'])
        
        print('✅ CSV文件生成完成！')
        print()
        print(f'📊 社区分级统计：')
        print(f'  高价值社区（1000+）：{len(tier1)} 个，{tier1_total:,} 个帖子（{tier1_total/grand_total*100:.1f}%）')
        print(f'  次高价值社区（500-999）：{len(tier2)} 个，{tier2_total:,} 个帖子（{tier2_total/grand_total*100:.1f}%）')
        print(f'  扩展语义社区（100-499）：{len(tier3)} 个，{tier3_total:,} 个帖子（{tier3_total/grand_total*100:.1f}%）')
        print(f'  低活跃社区（50-99）：{len(tier4)} 个，{tier4_total:,} 个帖子（{tier4_total/grand_total*100:.1f}%）')
        print(f'  待清理社区（0-49）：{len(tier5)} 个，{tier5_total:,} 个帖子（{tier5_total/grand_total*100:.1f}%）')
        print()
        print(f'📁 生成的文件：')
        print(f'  1. 高价值社区池_78个.csv')
        print(f'  2. 次高价值社区池_21个.csv')
        print(f'  3. 扩展语义社区池_77个.csv')
        print(f'  4. 待清理社区列表_47个.csv')
        print(f'  5. 社区分级汇总报告.csv')


if __name__ == '__main__':
    asyncio.run(generate_csv())

