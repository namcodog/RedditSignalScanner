import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def execute_kill_order():
    session = SessionFactory()
    try:
        # The Hit List - now includes r/askwomen
        kill_list = [
            'r/instacartshoppers', 
            'r/amazondspdrivers',
            'r/amazonflexdrivers',
            'r/walmartemployees',
            'r/amazonemployees',
            'r/fascamazon',
            'r/vent',
            'r/trueoffmychest',
            'r/sideproject',
            'r/askwomen' # Added to the blacklist
        ]
        
        print(f"--- 💀 再次执行死刑名单 (Executing Kill Order Again) ---")
        print(f"Targets: {kill_list}")
        
        # 1. Update Blacklist Status
        # We use IN clause
        formatted_list = "', '".join(kill_list)
        sql_blacklist = f"""
            UPDATE community_pool 
            SET is_blacklisted = true, 
                blacklist_reason = 'Noise/Labor_Complaints/Tumor',
                is_active = false
            WHERE name IN ('{formatted_list}')
            RETURNING name;
        """
        
        result = await session.execute(text(sql_blacklist))
        updated_rows = result.fetchall()
        await session.commit()
        
        print(f"\n✅ 已成功拉黑 {len(updated_rows)} 个社区 (Future crawling stopped).")
        for row in updated_rows:
            print(f"  - {row[0]}")

    except Exception as e:
        print(f"❌ Execution failed: {e}")
        await session.rollback()
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(execute_kill_order())