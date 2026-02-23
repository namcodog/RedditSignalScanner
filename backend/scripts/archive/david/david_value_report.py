import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def value_report():
    session = SessionFactory()
    try:
        print("--- 💰 社区含金量体检报告 (Community Value Audit) ---")
        
        # Simpler SQL construction
        sql_parts = [
            "WITH stats AS (",
            "    SELECT lower(p.subreddit) as sub_key, COUNT(p.id) as total_posts, COUNT(ps.post_id) FILTER (WHERE ps.business_pool = 'core') as core_posts",
            "    FROM posts_raw p",
            "    LEFT JOIN post_scores ps ON p.id = ps.post_id AND ps.is_latest = true",
            "    WHERE p.is_current = true",
            "    GROUP BY lower(p.subreddit)",
            ")",
            "SELECT cp.name, cp.vertical, COALESCE(s.total_posts, 0) as total_posts, COALESCE(s.core_posts, 0) as core_posts",
            "FROM community_pool cp",
            "LEFT JOIN stats s ON lower(cp.name) = s.sub_key",
            "WHERE cp.is_blacklisted = false AND cp.is_active = true",
            "ORDER BY cp.vertical, COALESCE(s.core_posts, 0) DESC"
        ]
        query = text(" ".join(sql_parts))
        
        result = await session.execute(query)
        rows = result.fetchall()
        
        verticals = {}
        for row in rows:
            v = row[1] or "Unclassified"
            if v not in verticals: verticals[v] = []
            verticals[v].append(row)
            
        for v, communities in verticals.items():
            print(f"\n======== {v} ========")
            print(f"{ 'Name':<25} | {'Gold':<6} | {'Total':<6} | {'Yield':<6}")
            print("-" * 55)
            
            for comm in communities:
                name = comm[0]
                total = comm[2]
                core = comm[3]
                ratio = (core / total * 100) if total > 0 else 0
                mark = "💎" if ratio > 50 else ("⚠️" if ratio < 10 and total > 100 else "")
                print(f"{name:<25} | {core:<6} | {total:<6} | {ratio:.1f}% {mark}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(value_report())
