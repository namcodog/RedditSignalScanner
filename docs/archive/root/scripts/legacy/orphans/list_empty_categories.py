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

def list_empty_and_cats():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🔍 Categories Audit Report\n")
    
    # 1. List Empty Categories
    print("=== 1. Communities with EMPTY Categories ===")
    empty_list = conn.execute(text("""
        SELECT name 
        FROM community_pool 
        WHERE is_active = true 
          AND (categories IS NULL OR categories = '[]'::jsonb)
        ORDER BY name
    """)).scalars().all()
    
    print(f"Count: {len(empty_list)}")
    for name in empty_list:
        print(f"  - {name}")
        
    # 2. List All Unique Tags
    print("\n=== 2. The REAL Category List (from DB) ===")
    # Explode the json array and count distinct
    tags = conn.execute(text("""
        SELECT DISTINCT jsonb_array_elements_text(categories) as tag
        FROM community_pool 
        WHERE is_active = true
        ORDER BY tag
    """)).scalars().all()
    
    print(f"Total Unique Tags Found: {len(tags)}")
    for tag in tags:
        print(f"  🏷️ {tag}")

    conn.close()

if __name__ == "__main__":
    list_empty_and_cats()
