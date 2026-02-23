import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def battle_map():
    session = SessionFactory()
    try:
        print("--- 🗺️ 社区战力分布图 (Community Battle Map) ---")
        
        # 1. Total Count
        res = await session.execute(text("SELECT count(*) FROM community_pool WHERE is_active = true"))
        total = res.scalar()
        print(f"⚔️ 总兵力: {total} 个活跃社区")
        
        # 2. Vertical Breakdown
        sql = """
            SELECT vertical, count(*), 
                   string_agg(CASE WHEN categories @> '["New_Injected"]' THEN name ELSE null END, ', ') as new_ones
            FROM community_pool 
            WHERE is_active = true 
            GROUP BY vertical 
            ORDER BY count(*) DESC
        """
        res = await session.execute(text(sql))
        rows = res.fetchall()
        
        print("\n🛡️ 各战区部署 (Deployment by Sector):")
        for r in rows:
            vert = r[0]
            count = r[1]
            new_str = r[2]
            
            # Get Top 3 existing (by posts count if possible, else random)
            # Since daily_posts is 0, we use posts_raw count for legacy
            top_sql = f"""
                SELECT p.name, count(pr.id) as cnt
                FROM community_pool p
                LEFT JOIN posts_raw pr ON p.name = pr.subreddit
                WHERE p.vertical = '{vert}' AND p.is_active = true
                GROUP BY p.name
                ORDER BY cnt DESC
                LIMIT 5
            """
            top_res = await session.execute(text(top_sql))
            top_rows = top_res.fetchall()
            
            top_names = [f"{tr[0]}({tr[1]})") for tr in top_rows]
            
            print(f"\n【{vert}】: {count} 个")
            print(f"   🔥 主力: {', '.join(top_names)}")
            if new_str:
                print(f"   🆕 新增: {new_str}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(battle_map())