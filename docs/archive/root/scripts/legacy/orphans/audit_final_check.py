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

def final_audit():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🏁 FINAL PRE-FLIGHT CHECK 2025-12-03\n")
    
    # 1. Community Pool
    active = conn.execute(text("SELECT count(*) FROM community_pool WHERE is_active=true")).scalar()
    inactive = conn.execute(text("SELECT count(*) FROM community_pool WHERE is_active=false")).scalar()
    untagged = conn.execute(text("SELECT count(*) FROM community_pool WHERE is_active=true AND categories='[]'::jsonb")).scalar()
    undescribed = conn.execute(text("SELECT count(*) FROM community_pool WHERE is_active=true AND description_keywords='{}'::jsonb")).scalar()
    
    print(f"🟢 Community Pool:")
    print(f"   - Active:   {active} (Target: ~207)")
    print(f"   - Inactive: {inactive} (Target: 0)")
    print(f"   - Untagged: {untagged} (Target: 0)")
    print(f"   - No Desc:  {undescribed} (Target: 0)")
    
    # 2. Cache
    cache_count = conn.execute(text("SELECT count(*) FROM community_cache")).scalar()
    cache_null = conn.execute(text("SELECT count(*) FROM community_cache WHERE last_crawled_at IS NULL")).scalar()
    
    print(f"\n🕸️ Community Cache:")
    print(f"   - Total:    {cache_count} (Target: = Active)")
    print(f"   - Fresh:    {cache_null} (Newcomers waiting for crawl)")
    
    # 3. Raw Storage
    raw_count = conn.execute(text("SELECT count(*) FROM posts_raw")).scalar()
    raw_orphan = conn.execute(text("SELECT count(*) FROM posts_raw WHERE subreddit NOT IN (SELECT name FROM community_pool)")).scalar()
    
    print(f"\n🔵 Raw Storage:")
    print(f"   - Total:    {raw_count}")
    print(f"   - Orphan:   {raw_orphan} (Target: 0)")
    
    # 4. Hot Storage
    hot_count = conn.execute(text("SELECT count(*) FROM posts_hot")).scalar()
    
    print(f"\n🔴 Hot Storage:")
    print(f"   - Total:    {hot_count} (Target: 0, ready for refill)")
    
    # 5. Vectors
    vec_count = conn.execute(text("SELECT count(*) FROM post_embeddings")).scalar()
    vec_orphan = conn.execute(text("SELECT count(*) FROM post_embeddings pe LEFT JOIN posts_raw pr ON pe.post_id = pr.id WHERE pr.id IS NULL")).scalar()
    
    print(f"\n🟣 Vector Embeddings:")
    print(f"   - Total:    {vec_count}")
    print(f"   - Orphan:   {vec_orphan} (Target: 0)")

    conn.close()

if __name__ == "__main__":
    final_audit()
