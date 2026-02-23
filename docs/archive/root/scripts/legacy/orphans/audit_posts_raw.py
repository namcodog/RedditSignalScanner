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

def audit_raw():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🧊 Auditing Posts Raw (Cold Storage)...")
    
    # 1. Total Count
    total = conn.execute(text("SELECT count(*) FROM posts_raw")).scalar()
    print(f"Total Rows: {total}")
    
    # 2. Completeness (Null checks)
    print("\n=== 2. Data Completeness ===")
    null_title = conn.execute(text("SELECT count(*) FROM posts_raw WHERE title IS NULL")).scalar()
    null_author = conn.execute(text("SELECT count(*) FROM posts_raw WHERE author_name IS NULL")).scalar()
    null_created = conn.execute(text("SELECT count(*) FROM posts_raw WHERE created_at IS NULL")).scalar()
    
    print(f"  NULL Title:   {null_title}")
    print(f"  NULL Author:  {null_author}")
    print(f"  NULL Created: {null_created}")
    
    # 3. Duplication (SCD2 Integrity)
    # Rule: For any given source_post_id, there should be exactly ONE row where is_current = true
    print("\n=== 3. SCD2 Integrity Check ===")
    
    # Correct query using is_current
    try:
        dupe_current = conn.execute(text("""
            SELECT source_post_id, count(*) 
            FROM posts_raw 
            WHERE is_current = true
            GROUP BY source_post_id 
            HAVING count(*) > 1
        """)).fetchall()
        print(f"  Duplicate Active Versions: {len(dupe_current)} (Should be 0)")
        if dupe_current:
            print(f"    Example: {dupe_current[0]}")
    except Exception as e:
        print(f"  ❌ Error checking SCD2: {e}")

    # 4. Time Travel
    print("\n=== 4. Time Logic Check ===")
    future_posts = conn.execute(text("SELECT count(*) FROM posts_raw WHERE created_at > NOW() + INTERVAL '1 day'")).scalar()
    ancient_posts = conn.execute(text("SELECT count(*) FROM posts_raw WHERE created_at < '2005-01-01'")).scalar() # Reddit founded 2005
    
    print(f"  Future Posts: {future_posts}")
    print(f"  Ancient Posts: {ancient_posts}")

    conn.close()

if __name__ == "__main__":
    audit_raw()
