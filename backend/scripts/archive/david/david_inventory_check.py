import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def deep_inventory():
    session = SessionFactory()
    try:
        print("--- 🗺️ 全局社区深度扫描 (Global Community Deep Scan) ---")
        
        # 1. Overall Stats
        print("\n📊 赛道分布 (Active Communities):")
        stats_sql = """
            SELECT vertical, COUNT(*), SUM(daily_posts) 
            FROM community_pool 
            WHERE is_blacklisted = false AND is_active = true
            GROUP BY vertical 
            ORDER BY count DESC
        """
        result = await session.execute(text(stats_sql))
        rows = result.fetchall()
        for row in rows:
            print(f"  • {row[0]}: {row[1]} 个社区")

        # 2. Deep Dive: Ecommerce_Business (The Problem Child)
        print("\n🛒 [Ecommerce_Business] 详细名单 (按名称排序):")
        ecom_sql = """
            SELECT name, categories 
            FROM community_pool 
            WHERE vertical = 'Ecommerce_Business' 
            AND is_blacklisted = false 
            AND is_active = true
            ORDER BY name
        """
        result = await session.execute(text(ecom_sql))
        ecom_subs = result.fetchall()
        
        # Grouping for better readability
        amazon_subs = []
        shopify_subs = []
        dropship_subs = []
        other_subs = []
        
        for row in ecom_subs:
            name = row[0]
            if 'amazon' in name.lower():
                amazon_subs.append(name)
            elif 'shopify' in name.lower():
                shopify_subs.append(name)
            elif 'dropship' in name.lower():
                dropship_subs.append(name)
            else:
                other_subs.append(name)
                
        print(f"  📦 Amazon 系 ({len(amazon_subs)}): {', '.join(amazon_subs)}")
        print(f"  🛍️ Shopify 系 ({len(shopify_subs)}): {', '.join(shopify_subs)}")
        print(f"  🚚 Dropship 系 ({len(dropship_subs)}): {', '.join(dropship_subs)}")
        print(f"  🧩 其他 ({len(other_subs)}): {', '.join(other_subs)}")

        # 3. Deep Dive: Home_Lifestyle
        print("\n🏠 [Home_Lifestyle] 详细名单:")
        home_sql = """
            SELECT name 
            FROM community_pool 
            WHERE vertical = 'Home_Lifestyle' 
            AND is_blacklisted = false 
            AND is_active = true
            ORDER BY name
        """
        result = await session.execute(text(home_sql))
        home_subs = [r[0] for r in result.fetchall()]
        print(f"  列表: {', '.join(home_subs)}")

        # 4. Check specifically for 'fc' or 'warehouse'
        print("\n🕵️‍♂️ 潜在漏网之鱼 (Suspects):")
        suspect_sql = """
            SELECT name, vertical 
            FROM community_pool 
            WHERE (name ILIKE '%fc%' OR name ILIKE '%warehouse%' OR name ILIKE '%union%')
            AND is_blacklisted = false 
            AND is_active = true
        """
        result = await session.execute(text(suspect_sql))
        suspects = result.fetchall()
        if suspects:
            for s in suspects:
                print(f"  - {s[0]} ({s[1]})")
        else:
            print("  - 暂无明显嫌疑。")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(deep_inventory())
