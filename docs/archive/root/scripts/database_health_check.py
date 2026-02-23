
import asyncio
import sys
from pathlib import Path
from sqlalchemy import text
from backend.app.db.session import SessionFactory

# Ensure backend is in pythonpath
sys.path.append(str(Path.cwd()))

async def database_health_check():
    async with SessionFactory() as session:
        print("=== 🏥 David's Database Health Check Report ===")
        
        # 1. 总体规模 (Total Volume)
        print("\n[1] 📦 资产盘点 (Inventory):")
        
        # Posts volume
        q_posts = text("SELECT count(*) FROM posts_raw WHERE is_current = true")
        total_posts = (await session.execute(q_posts)).scalar()
        
        # Comments volume
        q_comments = text("SELECT count(*) FROM comments")
        total_comments = (await session.execute(q_comments)).scalar()
        
        # Date Range
        q_dates = text("SELECT min(created_at), max(created_at) FROM posts_raw WHERE is_current = true")
        row = (await session.execute(q_dates)).one()
        min_date, max_date = row
        
        print(f"   - 帖子总数 (Posts): {total_posts:,}")
        print(f"   - 评论总数 (Comments): {total_comments:,}")
        print(f"   - 数据跨度: {min_date} 至 {max_date}")

        # 2. 价值分层 (Value Layering - Rulebook V1)
        print("\n[2] 💎 价值分层 (Based on 'rulebook_v1'):")
        
        q_pools = text("""
            SELECT business_pool, count(*), avg(value_score)::numeric(10,2)
            FROM post_scores 
            WHERE rule_version = 'rulebook_v1' AND is_latest = true
            GROUP BY business_pool
            ORDER BY count(*) DESC
        """)
        rows = await session.execute(q_pools)
        pool_stats = rows.fetchall()
        
        if not pool_stats:
            print("   ⚠️ No 'rulebook_v1' scores found!")
        
        for pool, count, avg_score in pool_stats:
            percent = (count / total_posts * 100) if total_posts else 0
            icon = "🌟" if pool == 'core' else ("🧪" if pool == 'lab' else "🗑️")
            print(f"   {icon} {pool.upper().ljust(5)}: {count:,} ({percent:.1f}%) - Avg Score: {avg_score}")

        # 3. 评论覆盖率 (Comment Coverage)
        print("\n[3] 💬 互动深度 (Engagement Depth):")
        
        # Core Posts (Score >= 8) coverage
        q_core_coverage = text("""
            SELECT 
                count(DISTINCT p.id) as core_posts,
                count(DISTINCT c.post_id) as core_with_comments
            FROM post_scores s
            JOIN posts_raw p ON s.post_id = p.id
            LEFT JOIN comments c ON p.id = c.post_id
            WHERE s.business_pool = 'core'
            AND s.rule_version = 'rulebook_v1' AND s.is_latest = true
        """)
        row = (await session.execute(q_core_coverage)).one()
        core_total, core_with = row
        core_rate = (core_with / core_total * 100) if core_total else 0
        
        print(f"   - 核心池(Core) 评论覆盖率: {core_rate:.1f}% ({core_with:,}/{core_total:,})")
        if core_rate < 80:
            print(f"     👉 建议：还有 {core_total - core_with:,} 个核心贴没挖评论，优先补全！")

        # High Value (Score >= 6) coverage
        q_high_coverage = text("""
            SELECT 
                count(DISTINCT p.id) as high_posts,
                count(DISTINCT c.post_id) as high_with_comments
            FROM post_scores s
            JOIN posts_raw p ON s.post_id = p.id
            LEFT JOIN comments c ON p.id = c.post_id
            WHERE s.value_score >= 6
            AND s.rule_version = 'rulebook_v1' AND s.is_latest = true
        """)
        row = (await session.execute(q_high_coverage)).one()
        high_total, high_with = row
        high_rate = (high_with / high_total * 100) if high_total else 0
        print(f"   - 高价值(Score>=6) 评论覆盖率: {high_rate:.1f}% ({high_with:,}/{high_total:,})")

        # 4. 社区贡献 (Community Contribution)
        print("\n[4] 🏘️ 社区含金量 Top 5 (By Core Posts):")
        q_top_communities = text("""
            SELECT p.subreddit, count(*) as core_count, avg(s.value_score)::numeric(10,1) as avg_score
            FROM post_scores s
            JOIN posts_raw p ON s.post_id = p.id
            WHERE s.business_pool = 'core'
            AND s.rule_version = 'rulebook_v1' AND s.is_latest = true
            GROUP BY p.subreddit
            ORDER BY core_count DESC
            LIMIT 5
        """)
        rows = await session.execute(q_top_communities)
        for r in rows:
            print(f"   - {r.subreddit.ljust(20)}: {r.core_count:,} Core Posts (Avg: {r.avg_score})")

        # 5. 评论质量 (Comment Quality)
        print("\n[5] 🗣️ 评论资产质量 (Comment Scores):")
        q_comment_scores = text("""
            SELECT business_pool, count(*) 
            FROM comment_scores 
            WHERE rule_version = 'rulebook_v1' AND is_latest = true
            GROUP BY business_pool
            ORDER BY count(*) DESC
        """)
        rows = await session.execute(q_comment_scores)
        c_stats = rows.fetchall()
        if not c_stats:
             print("   ⚠️ No 'rulebook_v1' comment scores found!")
        else:
            for pool, count in c_stats:
                print(f"   - {pool}: {count:,}")


if __name__ == "__main__":
    asyncio.run(database_health_check())
