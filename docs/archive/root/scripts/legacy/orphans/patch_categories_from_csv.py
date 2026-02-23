import os
import sys
import csv
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

def normalize_name(name):
    if not name: return ""
    name = name.strip().lower()
    if not name.startswith('r/'):
        return f"r/{name}"
    return name

def patch_categories():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    print("🩹 Patching Categories from 'reddit_200_new.csv'...\n")
    
    # 1. Load CSV Map
    csv_path = os.path.join(os.path.dirname(__file__), '../data/reddit_200_new.csv')
    category_map = {} # name -> category_string
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            # Check actual headers
            # Assuming headers are like 'Community', 'Category' based on context
            # If not, we might need to guess column index. Let's try DictReader first.
            
            for row in reader:
                # Explicit headers based on 'head' output: category,subreddit,description_zh,reason_zh
                # Handle potential BOM or whitespace by stripping keys if needed, but DictReader handles BOM with sig.
                
                # Try to match keys robustly
                comm = None
                cat = None
                desc = None
                reason = None
                
                for k, v in row.items():
                    k_clean = k.strip().lower()
                    if k_clean == 'subreddit':
                        comm = v
                    elif k_clean == 'category':
                        cat = v
                    elif k_clean == 'description_zh':
                        desc = v
                    elif k_clean == 'reason_zh':
                        reason = v
                
                if comm and cat:
                    meta = {}
                    if desc: meta['description'] = desc
                    if reason: meta['reason'] = reason
                    
                    category_map[normalize_name(comm)] = {
                        'category': cat.strip(),
                        'meta': meta
                    }
                    
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    print(f"Loaded {len(category_map)} mappings from CSV.")
    
    # 2. Update Database
    updated_count = 0
    
    # Get all active communities
    active_comms = conn.execute(text("SELECT name FROM community_pool WHERE is_active = true")).scalars().all()
    
    still_missing = []
    
    for name in active_comms:
        if name in category_map:
            data = category_map[name]
            cat_val = data['category']
            meta_val = data['meta']
            
            # Convert single string to JSON array for categories
            cat_json = json.dumps([cat_val])
            # Convert meta dict to JSON for description_keywords
            meta_json = json.dumps(meta_val, ensure_ascii=False)
            
            # Update both fields
            conn.execute(text("""
                UPDATE community_pool 
                SET categories = :cat,
                    description_keywords = :meta
                WHERE name = :name
            """), {"cat": cat_json, "meta": meta_json, "name": name})
            
            updated_count += 1
        else:
            still_missing.append(name)
            
    conn.commit()
    
    print(f"✅ Updated {updated_count} communities with categories.")
    print(f"\n⚠️ Communities NOT found in CSV (Missing Category Info): {len(still_missing)}")
    
    if still_missing:
        # Filter those that actually have empty categories in DB to be precise? 
        # The user asked for "not in CSV".
        for m in sorted(still_missing):
            print(f"  - {m}")

    conn.close()

if __name__ == "__main__":
    patch_categories()
