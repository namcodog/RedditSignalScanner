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

def standardize_tags():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    trans = conn.begin()
    
    print("🏷️ Standardizing Categories to the 'Sacred 7'...\n")
    
    valid_tags = {
        "Family_Parenting",
        "Food_Coffee_Lifestyle",
        "Frugal_Living",
        "Home_Lifestyle",
        "Minimal_Outdoor",
        "Tools_EDC",
        "Ecommerce_Business"
    }
    
    try:
        # 1. Cleanse: Remove invalid tags
        # This is tricky in SQL. Easier to fetch all, clean in Python, update back.
        # Given 200 rows, it's instant.
        
        all_comms = conn.execute(text("SELECT name, categories FROM community_pool WHERE is_active = true")).fetchall()
        
        cleaned_count = 0
        patched_count = 0
        
        for row in all_comms:
            name = row[0]
            current_cats = row[1] if row[1] else []
            
            # Step A: Filter for valid tags
            new_cats = [tag for tag in current_cats if tag in valid_tags]
            
            # Step B: Auto-assign Ecommerce_Business if empty AND matches keywords
            if not new_cats:
                # Heuristic for Ecommerce
                keywords = ['amazon', 'shopify', 'dropship', 'ecommerce', 'walmart', 'seo', 'marketing', 'business', 'fba', 'sellers', 'tiktok']
                if any(k in name.lower() for k in keywords):
                    new_cats = ["Ecommerce_Business"]
                    patched_count += 1
            
            # Step C: Update if changed
            # Compare sets to ignore order
            if set(new_cats) != set(current_cats):
                conn.execute(text("UPDATE community_pool SET categories = :cat WHERE name = :name"), 
                             {"cat": json.dumps(new_cats), "name": name})
                cleaned_count += 1
                
        trans.commit()
        print(f"✅ Standardization Complete.")
        print(f"   - Cleaned/Updated: {cleaned_count} communities")
        print(f"   - Auto-patched Ecommerce: {patched_count} communities")
        
        # Verify
        print("\n=== Final Verification ===")
        tags = conn.execute(text("""
            SELECT DISTINCT jsonb_array_elements_text(categories) as tag
            FROM community_pool 
            WHERE is_active = true
            ORDER BY tag
        """)).scalars().all()
        
        print(f"Total Unique Tags: {len(tags)}")
        for tag in tags:
            status = "✅" if tag in valid_tags else "❌"
            print(f"  {status} {tag}")
            
    except Exception as e:
        trans.rollback()
        print(f"❌ Error: {e}")

    conn.close()

if __name__ == "__main__":
    standardize_tags()
