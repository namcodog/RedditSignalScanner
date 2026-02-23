import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def gap_scan():
    session = SessionFactory()
    try:
        print("--- 🕳️ 覆盖率缺口扫描 (Coverage Gap Analysis) ---")
        
        # 1. Check Current Counts
        sql = """
            SELECT vertical, count(*) 
            FROM community_pool 
            WHERE is_blacklisted = false AND is_active = true 
            GROUP BY vertical 
            ORDER BY count(*) DESC
        """
        res = await session.execute(text(sql))
        rows = res.fetchall()
        
        print("\n📊 当前兵力分布 (Current Strength):")
        for r in rows:
            print(f"  - {r[0]}: {r[1]} communities")
            
        # 2. Check for "Missing Giants" (Common High Value Subs)
        # We check if they are in the pool (Active/Blacklisted) or Missing entirely
        candidates = {
            'Home_Lifestyle': ['r/lawncare', 'r/landscaping', 'r/hvac', 'r/organization', 'r/declutter', 'r/cleaning'],
            'Tools_EDC': ['r/justrolledintotheshop', 'r/mechanicadvice', 'r/electronics', 'r/askelectronics'],
            'Minimal_Outdoor': ['r/fishing', 'r/hunting', 'r/kayaking', 'r/camping'], # Camping exists?
            'Food_Coffee_Lifestyle': ['r/airfryer', 'r/instantpot', 'r/ricecooker', 'r/coffee'],
            'Family_Parenting': ['r/dogs', 'r/cats', 'r/pets', 'r/aquariums'], # Pet gap?
            'Ecommerce_Business': ['r/saas']
        }
        
        print("\n🔍 缺失巨头检测 (Missing Giants Check):")
        
        for vert, subs in candidates.items():
            print(f"\nChecking {vert} candidates:")
            for sub in subs:
                # Check DB
                check_sql = f"SELECT name, is_blacklisted, is_active FROM community_pool WHERE name ILIKE '{sub}'"
                res = await session.execute(text(check_sql))
                row = res.fetchone()
                
                if not row:
                    print(f"  [MISSING] {sub} - ❌ Not in DB (Recommend Add)")
                else:
                    status = "Active" if row[2] else ("Blacklisted" if row[1] else "Inactive")
                    print(f"  [FOUND]   {sub} - ✅ Status: {status}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(gap_scan())
