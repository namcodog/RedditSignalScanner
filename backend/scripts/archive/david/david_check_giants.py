import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def check_giants_status():
    session = SessionFactory()
    try:
        print("--- 🔍 检查新巨头状态 (Checking Giants) ---")
        
        targets = [
            'r/localllama', 'r/chatgpt', 
            'r/lawncare', 'r/malelivingspace', 
            'r/puppy101', 'r/battlestations'
        ]
        
        for name in targets:
            sql = f"SELECT name, vertical, is_active, tier FROM community_pool WHERE name = '{name}'"
            res = await session.execute(text(sql))
            row = res.fetchone()
            if row:
                print(f"✅ {row[0]}: Vertical='{row[1]}', Active={row[2]}, Tier='{row[3]}'")
            else:
                print(f"❌ {name}: NOT FOUND")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(check_giants_status())
