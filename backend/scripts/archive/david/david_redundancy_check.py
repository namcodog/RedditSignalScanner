import sys
import os
import asyncio
from sqlalchemy import text
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

async def redundancy_check():
    session = SessionFactory()
    try:
        print("--- 🕵️‍♂️ 社区冗余度与非标品审查 (Redundancy & Off-Product Scan) ---")
        
        # 1. Shopify Cluster
        print("\n🛒 Shopify 系分析:")
        s_sql = "SELECT name, daily_posts FROM community_pool WHERE name ILIKE '%shopify%' AND is_blacklisted = false ORDER BY daily_posts DESC"
        # Since daily_posts is 0, we use posts_raw count
        s_sql = """
            SELECT cp.name, COUNT(p.id) 
            FROM community_pool cp 
            LEFT JOIN posts_raw p ON cp.name = p.subreddit 
            WHERE cp.name ILIKE '%shopify%' AND cp.is_blacklisted = false 
            GROUP BY cp.name 
            ORDER BY count DESC
        """
        res = await session.execute(text(s_sql))
        rows = res.fetchall()
        for r in rows:
            print(f"  - {r[0]}: {r[1]} posts")

        # 2. Dropship Cluster
        print("\n🚚 Dropship 系分析:")
        d_sql = """
            SELECT cp.name, COUNT(p.id) 
            FROM community_pool cp 
            LEFT JOIN posts_raw p ON cp.name = p.subreddit 
            WHERE cp.name ILIKE '%dropship%' AND cp.is_blacklisted = false 
            GROUP BY cp.name 
            ORDER BY count DESC
        """
        res = await session.execute(text(d_sql))
        rows = res.fetchall()
        for r in rows:
            print(f"  - {r[0]}: {r[1]} posts")

        # 3. SEO Cluster
        print("\n🔍 SEO 系分析:")
        seo_sql = """
            SELECT cp.name, COUNT(p.id) 
            FROM community_pool cp 
            LEFT JOIN posts_raw p ON cp.name = p.subreddit 
            WHERE cp.name ILIKE '%seo%' AND cp.is_blacklisted = false 
            GROUP BY cp.name 
            ORDER BY count DESC
        """
        res = await session.execute(text(seo_sql))
        rows = res.fetchall()
        for r in rows:
            print(f"  - {r[0]}: {r[1]} posts")

        # 4. Service/Finance (Non-Product?)
        print("\n💳 纯服务/金融/非实物 (Service/Finance Check):")
        finance_targets = ['r/churning', 'r/financialindependence', 'r/povertyfinance', 'r/personalfinance', 'r/creditcards']
        f_sql = f"""
            SELECT cp.name, COUNT(p.id) 
            FROM community_pool cp 
            LEFT JOIN posts_raw p ON cp.name = p.subreddit 
            WHERE cp.name IN {tuple(finance_targets)} AND cp.is_blacklisted = false 
            GROUP BY cp.name 
            ORDER BY count DESC
        """
        res = await session.execute(text(f_sql))
        rows = res.fetchall()
        for r in rows:
            print(f"  - {r[0]}: {r[1]} posts")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(redundancy_check())
