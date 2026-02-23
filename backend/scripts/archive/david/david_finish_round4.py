import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def finish_round4():
    session = SessionFactory()
    try:
        targets = [
            'r/legomarket', 
            'r/knifeclub', 
            'r/edc', 
            'r/thriftstorehauls', 
            'r/gadgets', 
            'r/hydrohomies', 
            'r/amazonreviews'
        ]
        
        formatted_list = "', '".join(targets)
        
        print(f"--- 🔒 收尾工作 Round 4 (Locking & Cleaning) ---")
        
        # 1. Blacklist
        print(f"1. Updating Blacklist Status...")
        sql_blacklist = f"""
            UPDATE community_pool 
            SET is_blacklisted = true, 
                blacklist_reason = 'LowValue/Image_Heavy/Blacklisted_R4',
                is_active = false
            WHERE name IN ('{formatted_list}')
            RETURNING name;
        """
        res = await session.execute(text(sql_blacklist))
        await session.commit()
        print(f"   ✅ Blacklisted {res.rowcount} communities.")
        
        # 2. Cache Cleanup
        print(f"2. Cleaning Community Cache...")
        sql_cache = f"DELETE FROM community_cache WHERE community_name IN ('{formatted_list}')"
        res = await session.execute(text(sql_cache))
        await session.commit()
        print(f"   ✅ Removed {res.rowcount} from cache.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(finish_round4())
