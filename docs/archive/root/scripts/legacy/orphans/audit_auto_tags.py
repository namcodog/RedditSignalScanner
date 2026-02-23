import os
import sys
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def load_env_config():
    env_path = os.path.join(os.path.dirname(__file__), '../.env')
    load_dotenv(env_path)
    url = os.getenv('DATABASE_URL')
    if url and '+asyncpg' in url:
        return url.replace('+asyncpg', '+psycopg2')
    return url

def audit_tags():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🕵️ Auditing 'Ecommerce_Business' Auto-Tags...\n")
    
    # Get all Ecommerce communities
    ecom_comms = conn.execute(text("""
        SELECT name, description_keywords 
        FROM community_pool 
        WHERE is_active = true 
          AND categories @> '["Ecommerce_Business"]'
    """)).fetchall()
    
    # Core keywords that definitely mean Ecommerce
    # Removed 'store', 'business', 'marketing' as they might be too generic for other categories
    core_keywords = ['amazon', 'shopify', 'dropship', 'ecommerce', 'fba', 'seller', 'walmart', 'ali', 'logistics', 'print', 'merch', 'tiktok', 'etsy', 'ebay', 'flipping', 'freelance', 'ads', 'seo']
    
    suspicious = []
    
    for row in ecom_comms:
        name = row[0].lower()
        desc = row[1]
        
        is_obvious = any(k in name for k in core_keywords)
        
        if not is_obvious:
            suspicious.append((row[0], desc))
            
    print(f"Total Ecommerce Tagged: {len(ecom_comms)}")
    print(f"Suspicious / Ambiguous: {len(suspicious)}\n")
    
    for name, desc in suspicious:
        desc_text = desc.get('description_zh', 'N/A') if desc else 'N/A'
        print(f"❓ {name}")
        print(f"   Desc: {desc_text}")
        print(f"   Action: Keep or Re-tag?\n")

    conn.close()

if __name__ == "__main__":
    audit_tags()
