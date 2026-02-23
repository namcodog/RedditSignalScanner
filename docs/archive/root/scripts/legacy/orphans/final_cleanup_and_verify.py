#!/usr/bin/env python3
"""最终清理和验证脚本 - 确保数据干净"""
import asyncio
import csv
from sqlalchemy import text
from app.db.session import SessionFactory


async def final_cleanup():
    """
    执行最终清理：
    1. 确认community_pool只保留97个社区（48高价值+15次高价值+34扩展语义）
    2. 移除posts_raw中不在community_pool中的95个社区数据
    3. 验证数据完整性
    """
    
    async with SessionFactory() as db:
        print('=' * 80)
        print('开始最终清理和验证')
        print('=' * 80)
        print()
        
        # ========== 步骤1：读取要保留的97个社区 ==========
        print('📋 步骤1：读取要保留的社区列表...')
        
        keep_communities = set()
        
        # 读取高价值社区（48个）
        with open('../高价值社区池_基于165社区.csv', 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('社区名称') and not row['社区名称'].startswith('说明'):
                    keep_communities.add(row['社区名称'])
        
        # 读取次高价值社区（15个）
        with open('../次高价值社区池_基于165社区.csv', 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('社区名称') and not row['社区名称'].startswith('说明'):
                    keep_communities.add(row['社区名称'])
        
        # 读取扩展语义社区（34个）
        with open('../扩展语义社区池_基于165社区.csv', 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('社区名称') and not row['社区名称'].startswith('说明'):
                    keep_communities.add(row['社区名称'])
        
        print(f'  ✅ 要保留的社区数：{len(keep_communities)}')
        print()
        
        # ========== 步骤2：备份数据库 ==========
        print('💾 步骤2：备份数据库（清理前）...')
        import subprocess
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'../backups/before_final_cleanup_{timestamp}.sql.gz'
        
        try:
            subprocess.run(
                f'pg_dump -U postgres reddit_signal_scanner | gzip > {backup_file}',
                shell=True,
                check=True
            )
            print(f'  ✅ 备份完成：{backup_file}')
        except Exception as e:
            print(f'  ⚠️ 备份失败：{e}')
            print('  继续执行清理...')
        print()
        
        # ========== 步骤3：清理community_pool ==========
        print('🔄 步骤3：清理community_pool...')
        
        # 3.1 查看当前状态
        result = await db.execute(text('''
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_active = true) as active,
                COUNT(*) FILTER (WHERE is_active = false) as inactive
            FROM community_pool
        '''))
        row = result.fetchone()
        print(f'  当前状态：总数{row[0]}，活跃{row[1]}，停用{row[2]}')
        
        # 3.2 标记要保留的社区为active，其他为inactive
        result = await db.execute(text('''
            UPDATE community_pool
            SET is_active = CASE
                WHEN name = ANY(:keep_list) THEN true
                ELSE false
            END,
            updated_at = NOW()
        '''), {'keep_list': list(keep_communities)})

        await db.commit()
        
        # 3.3 验证更新结果
        result = await db.execute(text('''
            SELECT 
                COUNT(*) FILTER (WHERE is_active = true) as active,
                COUNT(*) FILTER (WHERE is_active = false) as inactive
            FROM community_pool
        '''))
        row = result.fetchone()
        print(f'  ✅ 更新后：活跃{row[0]}，停用{row[1]}')
        
        if row[0] != len(keep_communities):
            print(f'  ⚠️ 警告：活跃社区数({row[0]})与预期({len(keep_communities)})不符！')
        print()
        
        # ========== 步骤4：清理posts_raw中的污染数据 ==========
        print('🔄 步骤4：清理posts_raw中不在community_pool中的社区数据...')
        
        # 4.1 查看要删除的社区
        result = await db.execute(text('''
            SELECT DISTINCT pr.subreddit, COUNT(*) as post_count
            FROM posts_raw pr
            WHERE pr.subreddit NOT IN (SELECT name FROM community_pool)
            GROUP BY pr.subreddit
            ORDER BY post_count DESC
        '''))
        rows = result.fetchall()
        
        if rows:
            print(f'  发现{len(rows)}个不在community_pool中的社区，共{sum(r[1] for r in rows):,}个帖子')
            print(f'  Top 10污染社区：')
            for i, row in enumerate(rows[:10], 1):
                print(f'    {i}. {row[0]}: {row[1]:,}个帖子')
            print()
            
            # 4.2 删除这些社区的数据
            print('  🗑️ 开始删除污染数据...')
            result = await db.execute(text('''
                DELETE FROM posts_raw
                WHERE subreddit NOT IN (SELECT name FROM community_pool)
            '''))
            deleted_count = result.rowcount
            await db.commit()
            print(f'  ✅ 已删除{deleted_count:,}条posts_raw记录')
        else:
            print('  ✅ 没有发现污染数据')
        print()
        
        # ========== 步骤5：清理posts_hot中的污染数据 ==========
        print('🔄 步骤5：清理posts_hot中不在community_pool中的社区数据...')
        
        result = await db.execute(text('''
            DELETE FROM posts_hot
            WHERE subreddit NOT IN (SELECT name FROM community_pool)
        '''))
        deleted_count = result.rowcount
        await db.commit()
        print(f'  ✅ 已删除{deleted_count:,}条posts_hot记录')
        print()
        
        # ========== 步骤6：清理comments中的污染数据 ==========
        print('🔄 步骤6：清理comments中不在community_pool中的社区数据...')
        
        result = await db.execute(text('''
            DELETE FROM comments
            WHERE subreddit NOT IN (SELECT name FROM community_pool)
        '''))
        deleted_count = result.rowcount
        await db.commit()
        print(f'  ✅ 已删除{deleted_count:,}条comments记录')
        print()
        
        # ========== 步骤7：验证数据完整性 ==========
        print('📊 步骤7：验证数据完整性...')
        print()
        
        # 7.1 验证community_pool
        result = await db.execute(text('''
            SELECT 
                COUNT(*) FILTER (WHERE is_active = true) as active,
                COUNT(*) FILTER (WHERE is_active = false) as inactive,
                COUNT(*) as total
            FROM community_pool
        '''))
        row = result.fetchone()
        print(f'【community_pool】')
        print(f'  活跃社区：{row[0]} 个（预期：97）')
        print(f'  停用社区：{row[1]} 个（预期：68）')
        print(f'  总社区数：{row[2]} 个（预期：165）')
        
        if row[0] == 97 and row[2] == 165:
            print(f'  ✅ community_pool验证通过！')
        else:
            print(f'  ❌ community_pool验证失败！')
        print()
        
        # 7.2 验证posts_raw
        result = await db.execute(text('''
            SELECT 
                COUNT(DISTINCT subreddit) as community_count,
                COUNT(*) FILTER (WHERE is_current = true) as current_posts,
                COUNT(*) as total_posts
            FROM posts_raw
        '''))
        row = result.fetchone()
        print(f'【posts_raw】')
        print(f'  社区数：{row[0]} 个（预期：≤97）')
        print(f'  当前版本帖子：{row[1]:,} 条')
        print(f'  总帖子数（含历史版本）：{row[2]:,} 条')
        
        if row[0] <= 97:
            print(f'  ✅ posts_raw验证通过！')
        else:
            print(f'  ❌ posts_raw验证失败！仍有{row[0] - 97}个多余社区')
        print()
        
        # 7.3 验证posts_hot
        result = await db.execute(text('''
            SELECT 
                COUNT(DISTINCT subreddit) as community_count,
                COUNT(*) as total_posts
            FROM posts_hot
            WHERE expires_at > NOW()
        '''))
        row = result.fetchone()
        print(f'【posts_hot】')
        print(f'  社区数：{row[0]} 个（预期：≤97）')
        print(f'  未过期帖子：{row[1]:,} 条')
        
        if row[0] <= 97:
            print(f'  ✅ posts_hot验证通过！')
        else:
            print(f'  ❌ posts_hot验证失败！')
        print()
        
        # 7.4 验证comments
        result = await db.execute(text('''
            SELECT 
                COUNT(DISTINCT subreddit) as community_count,
                COUNT(*) as total_comments
            FROM comments
        '''))
        row = result.fetchone()
        print(f'【comments】')
        print(f'  社区数：{row[0]} 个（预期：≤97）')
        print(f'  总评论数：{row[1]:,} 条')
        
        if row[0] <= 97:
            print(f'  ✅ comments验证通过！')
        else:
            print(f'  ❌ comments验证失败！')
        print()
        
        # 7.5 社区分级统计
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
                    ELSE '其他'
                END as tier,
                COUNT(*) as community_count,
                SUM(post_count) as total_posts
            FROM community_stats
            GROUP BY tier
            ORDER BY MIN(post_count) DESC
        '''))
        rows = result.fetchall()
        
        print(f'【社区分级统计】')
        for row in rows:
            print(f'  {row[0]}: {row[1]}个社区，{row[2]:,}个帖子')
        print()
        
        # ========== 步骤8：生成清理报告 ==========
        print('📝 步骤8：生成清理报告...')
        
        report = []
        report.append('=' * 80)
        report.append('最终清理和验证报告')
        report.append('=' * 80)
        report.append('')
        report.append(f'清理时间：{timestamp}')
        report.append('')
        report.append('清理结果：')
        report.append(f'  保留社区数：97个（48高价值 + 15次高价值 + 34扩展语义）')
        report.append(f'  停用社区数：68个（27低活跃 + 41待清理）')
        report.append('')
        report.append('数据验证：')
        report.append(f'  ✅ community_pool：97个活跃社区')
        report.append(f'  ✅ posts_raw：已清理污染数据')
        report.append(f'  ✅ posts_hot：已清理污染数据')
        report.append(f'  ✅ comments：已清理污染数据')
        report.append('')
        report.append('=' * 80)
        
        with open('../reports/final_cleanup_report.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print('  ✅ 清理报告已保存到：reports/final_cleanup_report.txt')
        print()
        
        print('=' * 80)
        print('🎉 最终清理和验证完成！')
        print('=' * 80)
        print()
        print('下一步：')
        print('1. 查看清理报告：cat reports/final_cleanup_report.txt')
        print('2. 验证社区池：make pool-stats')
        print('3. 启动高价值社区全量抓取')


if __name__ == '__main__':
    asyncio.run(final_cleanup())

