import os
import sys
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

def audit_pool_reality():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("📸 SNAPSHOT: Community Pool Reality Check\n")
    
    # 1. Basic Headcount
    print("=== 1. Headcount & Status ===")
    total = conn.execute(text("SELECT count(*) FROM community_pool")).scalar()
    active = conn.execute(text("SELECT count(*) FROM community_pool WHERE is_active = true")).scalar()
    inactive = conn.execute(text("SELECT count(*) FROM community_pool WHERE is_active = false")).scalar()
    
    print(f"Total Communities: {total}")
    print(f"  ✅ Active:   {active}")
    print(f"  ❌ Inactive: {inactive} (Should be 0)")
    
    # 2. Data Asset Correlation (Old vs New)
    print("\n=== 2. Veterans vs Newcomers ===")
    # Veterans: Active communities that HAVE data in posts_raw
    veterans = conn.execute(text("""
        SELECT count(DISTINCT p.name) 
        FROM community_pool p
        JOIN posts_raw r ON p.name = r.subreddit
        WHERE p.is_active = true
    """)).scalar()
    
    # Newcomers: Active communities with NO data in posts_raw
    newcomers = conn.execute(text("""
        SELECT count(DISTINCT p.name) 
        FROM community_pool p
        LEFT JOIN posts_raw r ON p.name = r.subreddit
        WHERE p.is_active = true AND r.id IS NULL
    """)).scalar()
    
    print(f"  🎖️ Veterans (Have Data): {veterans} (The 120 Survivors)")
    print(f"  🆕 Newcomers (Empty):    {newcomers} (From CSV)")
    print(f"  (Check: {veterans} + {newcomers} = {active}?)")

    # 3. Categories Health
    print("\n=== 3. Categories Tags Status ===")
    empty_cats = conn.execute(text("SELECT count(*) FROM community_pool WHERE categories = '[]'::jsonb")).scalar()
    tagged_cats = conn.execute(text("SELECT count(*) FROM community_pool WHERE jsonb_array_length(categories) > 0")).scalar()
    
    print(f"  🏷️ Tagged Communities: {tagged_cats} (Recovered from old data)")
    print(f"  ⚪ Empty Tags:         {empty_cats} (New or Reset)")

    # 4. Sample Inspection
    print("\n=== 4. Dossier Inspection (Samples) ===")
    
    print("--- Sample: Veteran (High Traffic) ---")
    vet_sample = conn.execute(text("""
        SELECT p.name, p.tier, p.categories, count(r.id) as post_count
        FROM community_pool p
        JOIN posts_raw r ON p.name = r.subreddit
        GROUP BY p.name, p.tier, p.categories
        ORDER BY post_count DESC
        LIMIT 1
    """)).fetchone()
    if vet_sample:
        print(f"  Name: {vet_sample[0]}")
        print(f"  Tier: {vet_sample[1]}")
        print(f"  Tags: {vet_sample[2]}")
        print(f"  Data: {vet_sample[3]} posts")

    print("\n--- Sample: Newcomer (From CSV) ---")
    new_sample = conn.execute(text("""
        SELECT p.name, p.tier, p.categories
        FROM community_pool p
        LEFT JOIN posts_raw r ON p.name = r.subreddit
        WHERE r.id IS NULL
        ORDER BY p.created_at DESC
        LIMIT 1
    """)).fetchone()
    if new_sample:
        print(f"  Name: {new_sample[0]}")
        print(f"  Tier: {new_sample[1]}")
        print(f"  Tags: {new_sample[2]}")
        print(f"  Data: 0 posts (Awaiting Crawl)")

    conn.close()

if __name__ == "__main__":
    audit_pool_reality()
