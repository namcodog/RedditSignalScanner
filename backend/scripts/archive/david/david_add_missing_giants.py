import sys
import os
import asyncio
import json
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def add_missing_giants():
    session = SessionFactory()
    try:
        print("--- ➕ 补充核心巨头 (Injecting Missing Giants) ---")
        
        # Format: (Name, Vertical, Reason)
        new_recruits = [
            # 1. The Pet Void (Huge Market)
            ('r/dogs', 'Family_Parenting', 'Core Pet Health/Food/Gear'),
            ('r/cats', 'Family_Parenting', 'Core Pet Health/Food/Gear'),
            ('r/pets', 'Family_Parenting', 'General Pet Care'),
            ('r/aquariums', 'Home_Lifestyle', 'High Value Hobby/Equipment'),
            
            # 2. The Appliance/Kitchen Void (Product Specific)
            ('r/airfryer', 'Food_Coffee_Lifestyle', 'Specific Appliance/Recipes'),
            ('r/instantpot', 'Food_Coffee_Lifestyle', 'Specific Appliance/Recipes'),
            ('r/robotvacuums', 'Home_Lifestyle', 'High Tech Home Appliance'),
            ('r/coffee', 'Food_Coffee_Lifestyle', 'Core Coffee Gear (Re-verify active)'),
            
            # 3. The Yard/Garage Void (Maintenance)
            ('r/lawncare', 'Home_Lifestyle', 'Lawn Chemicals/Mowers/Tools'),
            ('r/hvac', 'Home_Lifestyle', 'AC/Heating Units/Thermostats'),
            ('r/cleaning', 'Home_Lifestyle', 'Cleaning Chemicals/Tools'),
            ('r/organization', 'Home_Lifestyle', 'Storage/Containers'),
            ('r/declutter', 'Home_Lifestyle', 'Storage/Minimalism'),
            
            # 4. The Tech/Tools Void
            ('r/electronics', 'Tools_EDC', 'Soldering/Components/Tools'),
            ('r/askelectronics', 'Tools_EDC', 'Repair/Tools'),
            ('r/justrolledintotheshop', 'Tools_EDC', 'Mechanic Humor/Failures'),
            
            # 5. Missing Ecommerce
            ('r/saas', 'Ecommerce_Business', 'Software Products/B2B')
        ]
        
        added_count = 0
        
        for name, vertical, reason in new_recruits:
            # Check if exists (Active or Blacklisted)
            check_sql = f"SELECT name FROM community_pool WHERE name ILIKE '{name}'"
            res = await session.execute(text(check_sql))
            if res.fetchone():
                print(f"  - {name} already exists. Skipping.")
                continue
                
            # Insert with categories
            print(f"  - Adding {name} ({vertical})...")
            # Using raw SQL with cast for jsonb if needed, or just string '[]' depending on driver
            # Postgres usually handles text to jsonb conversion
            insert_sql = """
                INSERT INTO community_pool (name, vertical, tier, is_active, created_at, updated_at, categories)
                VALUES (:name, :vertical, 1, true, NOW(), NOW(), '[]')
            """
            await session.execute(text(insert_sql), {"name": name, "vertical": vertical})
            added_count += 1
            
        await session.commit()
        print(f"\n✅ Successfully added {added_count} new giants to the pool.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(add_missing_giants())