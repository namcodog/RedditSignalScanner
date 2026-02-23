import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def full_list_inventory():
    session = SessionFactory()
    try:
        print("--- 🗺️ 全局社区完整名单 (Full Community Roster) ---")
        
        # Get all active verticals
        v_sql = "SELECT DISTINCT vertical FROM community_pool WHERE is_blacklisted = false AND is_active = true ORDER BY vertical"
        result = await session.execute(text(v_sql))
        verticals = [r[0] for r in result.fetchall()]
        
        for v in verticals:
            print(f"\n======== {v} ========")
            sub_sql = f"""
                SELECT name, daily_posts 
                FROM community_pool 
                WHERE vertical = '{v}' 
                AND is_blacklisted = false 
                AND is_active = true
                ORDER BY name
            """
            res = await session.execute(text(sub_sql))
            subs = res.fetchall()
            
            print(f"Total: {len(subs)}")
            # Print in comma separated lines, maybe 5 per line? 
            # Or just a clean list. User said "Fully listed out".
            # I will print them as a list.
            names = [f"{r[0]}" for r in subs]
            print(", ".join(names))

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(full_list_inventory())
