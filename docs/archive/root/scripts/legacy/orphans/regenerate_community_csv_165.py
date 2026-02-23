#!/usr/bin/env python3
"""基于community_pool的165个社区重新生成分级CSV"""
import asyncio
import csv
from sqlalchemy import text
from app.db.session import SessionFactory


async def regenerate_csv():
    async with SessionFactory() as db:
        # 获取community_pool中所有社区的详细统计
        result = await db.execute(text('''
            WITH community_stats AS (
                SELECT 
                    cp.name as subreddit,
                    COUNT(pr.id) as total_posts,
                    COUNT(DISTINCT DATE(pr.created_at)) as active_days,
                    MIN(pr.created_at) as earliest_post,
                    MAX(pr.created_at) as latest_post,
                    AVG(pr.score)::INTEGER as avg_score,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pr.score)::INTEGER as median_score,
                    AVG(pr.num_comments)::INTEGER as avg_comments,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pr.num_comments)::INTEGER as median_comments,
                    COUNT(CASE WHEN pr.score >= 100 THEN 1 END) as high_score_posts,
                    COUNT(CASE WHEN pr.num_comments >= 50 THEN 1 END) as high_comment_posts,
                    COUNT(CASE WHEN pr.score >= 100 AND pr.num_comments >= 50 THEN 1 END) as high_quality_posts,
                    COUNT(CASE WHEN pr.created_at >= NOW() - INTERVAL '12 months' THEN 1 END) as posts_last_12m,
                    COUNT(CASE WHEN pr.created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as posts_last_30d,
                    cp.is_active
                FROM community_pool cp
                LEFT JOIN posts_raw pr ON cp.name = pr.subreddit AND pr.is_current = true
                GROUP BY cp.name, cp.is_active
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
                ROUND(high_quality_posts::NUMERIC / NULLIF(total_posts, 0) * 100, 2) as quality_rate,
                ROUND(posts_last_30d::NUMERIC / NULLIF(total_posts, 0) * 100, 2) as recent_activity_rate,
                is_active
            FROM community_stats
            ORDER BY total_posts DESC
        '''))
        
        all_communities = result.fetchall()
        
        # 分级（仅统计有帖子的社区）
        tier1 = []  # 1000+
        tier2 = []  # 500-999
        tier3 = []  # 100-499
        tier4 = []  # 50-99
        tier5 = []  # 0-49
        
        for row in all_communities:
            total_posts = row[1] or 0
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
            '近期活跃度(%)',
            '是否活跃'
        ]
        
        # 生成CSV文件
        def write_csv(filename, tier_data, description, strategy):
            with open(f'../{filename}', 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerow([f'说明：{description}'])
                writer.writerow([f'抓取策略：{strategy}'])
                writer.writerow([])
                for row in tier_data:
                    writer.writerow([
                        row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8],
                        row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16]
                    ])
        
        # 1. 高价值社区
        write_csv(
            '高价值社区池_基于165社区.csv',
            tier1,
            f'这{len(tier1)}个社区是核心数据源，建议抓取全量帖子+全量评论',
            '全量抓取，每15分钟增量更新'
        )
        
        # 2. 次高价值社区
        write_csv(
            '次高价值社区池_基于165社区.csv',
            tier2,
            f'这{len(tier2)}个社区是补充数据源，建议抓取最近12个月帖子+评论',
            '抓取最近12个月数据，每30分钟增量更新'
        )
        
        # 3. 扩展语义社区
        write_csv(
            '扩展语义社区池_基于165社区.csv',
            tier3,
            f'这{len(tier3)}个社区提供语义多样性，建议保留但降低抓取频率',
            '抓取最近12个月数据，每2小时增量更新'
        )
        
        # 4. 低活跃社区
        write_csv(
            '低活跃社区池_基于165社区.csv',
            tier4,
            f'这{len(tier4)}个社区活跃度较低，建议评估后决定',
            '待评估'
        )
        
        # 5. 待清理社区
        write_csv(
            '待清理社区列表_基于165社区.csv',
            tier5,
            f'这{len(tier5)}个社区活跃度极低，建议从抓取池中移除',
            '停止抓取，保留历史数据'
        )
        
        # 6. 生成汇总报告
        tier1_total = sum(row[1] or 0 for row in tier1)
        tier2_total = sum(row[1] or 0 for row in tier2)
        tier3_total = sum(row[1] or 0 for row in tier3)
        tier4_total = sum(row[1] or 0 for row in tier4)
        tier5_total = sum(row[1] or 0 for row in tier5)
        grand_total = tier1_total + tier2_total + tier3_total + tier4_total + tier5_total
        
        with open('../社区分级汇总报告_基于165社区.csv', 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['社区分级汇总报告（基于community_pool的165个社区）'])
            writer.writerow([])
            writer.writerow(['级别', '帖子数范围', '社区数量', '总帖子数', '占比', '抓取策略'])
            
            writer.writerow([
                '高价值社区',
                '1000+',
                len(tier1),
                tier1_total,
                f'{tier1_total/grand_total*100:.1f}%' if grand_total > 0 else '0%',
                '全量抓取（帖子+评论），每15分钟更新'
            ])
            writer.writerow([
                '次高价值社区',
                '500-999',
                len(tier2),
                tier2_total,
                f'{tier2_total/grand_total*100:.1f}%' if grand_total > 0 else '0%',
                '抓取最近12个月（帖子+评论），每30分钟更新'
            ])
            writer.writerow([
                '扩展语义社区',
                '100-499',
                len(tier3),
                tier3_total,
                f'{tier3_total/grand_total*100:.1f}%' if grand_total > 0 else '0%',
                '抓取最近12个月（仅帖子），每2小时更新'
            ])
            writer.writerow([
                '低活跃社区',
                '50-99',
                len(tier4),
                tier4_total,
                f'{tier4_total/grand_total*100:.1f}%' if grand_total > 0 else '0%',
                '待评估'
            ])
            writer.writerow([
                '待清理社区',
                '0-49',
                len(tier5),
                tier5_total,
                f'{tier5_total/grand_total*100:.1f}%' if grand_total > 0 else '0%',
                '停止抓取，保留历史数据'
            ])
            writer.writerow([])
            writer.writerow(['总计', '', len(all_communities), grand_total, '100.0%', ''])
            writer.writerow([])
            writer.writerow(['保留社区数', f'{len(tier1) + len(tier2) + len(tier3)} 个'])
            writer.writerow(['丢弃社区数', f'{len(tier5)} 个'])
        
        print('✅ CSV文件生成完成！')
        print()
        print(f'📊 社区分级统计（基于community_pool的165个社区）：')
        print(f'  高价值社区（1000+）：{len(tier1)} 个，{tier1_total:,} 个帖子（{tier1_total/grand_total*100:.1f}%）')
        print(f'  次高价值社区（500-999）：{len(tier2)} 个，{tier2_total:,} 个帖子（{tier2_total/grand_total*100:.1f}%）')
        print(f'  扩展语义社区（100-499）：{len(tier3)} 个，{tier3_total:,} 个帖子（{tier3_total/grand_total*100:.1f}%）')
        print(f'  低活跃社区（50-99）：{len(tier4)} 个，{tier4_total:,} 个帖子（{tier4_total/grand_total*100:.1f}%）')
        print(f'  待清理社区（0-49）：{len(tier5)} 个，{tier5_total:,} 个帖子（{tier5_total/grand_total*100:.1f}%）')
        print()
        print(f'📁 生成的文件：')
        print(f'  1. 高价值社区池_基于165社区.csv')
        print(f'  2. 次高价值社区池_基于165社区.csv')
        print(f'  3. 扩展语义社区池_基于165社区.csv')
        print(f'  4. 低活跃社区池_基于165社区.csv')
        print(f'  5. 待清理社区列表_基于165社区.csv')
        print(f'  6. 社区分级汇总报告_基于165社区.csv')


if __name__ == '__main__':
    asyncio.run(regenerate_csv())

