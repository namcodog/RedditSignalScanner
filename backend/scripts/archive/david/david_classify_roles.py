import sys
import os
import asyncio
import re
from sqlalchemy import text
from collections import defaultdict
# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.session import SessionFactory

# Keywords to distinguish "Seller/Business" from "Consumer/User"
SELLER_KEYWORDS = {
    'customer', 'client', 'shipping', 'supplier', 'agent', 'profit', 'margin', 
    'roi', 'ads', 'campaign', 'traffic', 'store', 'shop', 'brand', 'sourcing',
    'wholesale', 'fba', 'pl', 'label', 'inventory', 'refund', 'buyer'
}

CONSUMER_KEYWORDS = {
    'bought', 'buy', 'looking for', 'recommend', 'suggestion', 'broke', 'broken',
    'review', 'love', 'hate', 'quality', 'price', 'deal', 'cheap', 'expensive',
    'wife', 'husband', 'kid', 'house', 'home', 'room', 'kitchen', 'usage', 'used'
}

async def classify_communities():
    session = SessionFactory()
    try:
        print("--- 👥 社区画像分层：买家 vs 卖家 (Buyer vs Seller Split) ---")
        
        # Get all active communities
        sql = "SELECT name, vertical FROM community_pool WHERE is_blacklisted = false AND is_active = true"
        res = await session.execute(text(sql))
        communities = res.fetchall()
        
        print(f"Analyzing {len(communities)} communities...")
        
        results = {
            'B2B_Seller': [],
            'B2C_Consumer': [],
            'Mixed': []
        }
        
        for name, vertical in communities:
            # Fetch last 30 titles + bodies
            p_sql = f"SELECT title, body FROM posts_raw WHERE subreddit = '{name}' ORDER BY created_at DESC LIMIT 30"
            p_res = await session.execute(text(p_sql))
            posts = p_res.fetchall()
            
            if not posts:
                results['Mixed'].append((name, vertical, 0, 0, "No Data"))
                continue
                
            seller_score = 0
            consumer_score = 0
            
            text_content = " ".join([f"{r[0]} {r[1] or ''}" for r in posts]).lower()
            
            # Simple keyword counting
            for word in SELLER_KEYWORDS:
                seller_score += text_content.count(word)
            for word in CONSUMER_KEYWORDS:
                consumer_score += text_content.count(word)
            
            # Normalize
            total = seller_score + consumer_score
            if total == 0:
                ratio = 0.5
            else:
                ratio = seller_score / total
            
            # Classification
            if ratio > 0.7:
                tag = 'B2B_Seller'
            elif ratio < 0.3:
                tag = 'B2C_Consumer'
            else:
                tag = 'Mixed'
                
            results[tag].append((name, vertical, seller_score, consumer_score, f"{ratio:.2f}"))

        # Output Report
        print(f"\n📊 分布概览 (Distribution):")
        print(f"  🏢 B2B 卖家/搞钱社区: {len(results['B2B_Seller'])}")
        print(f"  🏠 B2C 消费者/生活社区: {len(results['B2C_Consumer'])}")
        print(f"  ⚖️ 混合/模糊社区: {len(results['Mixed'])}")
        
        print(f"\n🏢 B2B (Seller) Top 20 Examples:")
        for r in sorted(results['B2B_Seller'], key=lambda x: float(x[4]), reverse=True)[:20]:
            print(f"  - {r[0]:<25} | Score: {r[4]} | {r[1]}")

        print(f"\n🏠 B2C (Consumer) Top 20 Examples:")
        for r in sorted(results['B2C_Consumer'], key=lambda x: float(x[4]), reverse=False)[:20]:
            print(f"  - {r[0]:<25} | Score: {r[4]} | {r[1]}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(classify_communities())
