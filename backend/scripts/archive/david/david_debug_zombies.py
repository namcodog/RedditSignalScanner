import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def debug_round5_zombies():
    session = SessionFactory()
    try:
        print("--- 🧟‍♂️ Round 5 残党诊断 (Round 5 Zombie Debug) ---")
        
        zombies = ['r/personalfinance', 'r/churning', 'r/shopifywebsites']
        
        for z in zombies:
            print(f"\n🔍 Checking {z}...")
            
            # Check Pool Status
            pool_sql = f"SELECT name, is_blacklisted, is_active FROM community_pool WHERE name = '{z}'"
            res = await session.execute(text(pool_sql))
            pool_row = res.fetchone()
            
            if pool_row:
                print(f"   Pool: Name='{pool_row[0]}', Blacklisted={pool_row[1]}, Active={pool_row[2]}")
            else:
                print(f"   Pool: Not Found!")
                
            # Check Posts Count
            posts_sql = f"SELECT count(*) FROM posts_raw WHERE subreddit = '{z}'"
            res = await session.execute(text(posts_sql))
            count = res.scalar()
            print(f"   Posts: {count}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(debug_round5_zombies())
