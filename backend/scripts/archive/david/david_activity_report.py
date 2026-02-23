import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def activity_report():
    session = SessionFactory()
    try:
        print("--- 📉 社区活跃度体检 (Community Activity Audit) ---")
        print("指标：日均发帖量 (Daily Posts)")
        
        # Query active communities ordered by daily_posts ASC
        sql = """
            SELECT name, vertical, daily_posts, tier 
            FROM community_pool 
            WHERE is_blacklisted = false AND is_active = true
            ORDER BY daily_posts ASC
        """
        
        result = await session.execute(text(sql))
        rows = result.fetchall()
        
        print(f"Total Active Communities: {len(rows)}")
        
        # Define Thresholds
        zombies = [] # < 0.5 posts/day
        sleepy = []  # 0.5 - 2 posts/day
        active = []  # > 2
        
        for row in rows:
            name, vertical, daily, tier = row
            # daily_posts might be None?
            d = daily if daily is not None else 0
            
            item = f"{name} ({vertical}) - {d:.1f}/day"
            
            if d < 0.5:
                zombies.append(item)
            elif d < 2.0:
                sleepy.append(item)
            else:
                active.append(item)
                
        print(f"\n🧟‍♂️ 僵尸/停滞社区 (< 0.5 帖/天) - 共 {len(zombies)} 个:")
        for z in zombies:
            print(f"  - {z}")
            
        print(f"\n😴 瞌睡社区 (0.5 - 2.0 帖/天) - 共 {len(sleepy)} 个:")
        for s in sleepy:
            print(f"  - {s}")
            
        print(f"\n🚀 活跃社区 (> 2.0 帖/天) - 共 {len(active)} 个")
        # Don't list all active, just count.

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(activity_report())
