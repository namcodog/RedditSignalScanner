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

def init_and_audit_cache():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    trans = conn.begin()
    
    print("🔧 Initializing Missing Cache Records...\n")
    
    try:
        # 1. Init Logic
        # Insert into cache for any ACTIVE pool member NOT in cache
        # This is a safe bulk insert
        init_sql = """
            INSERT INTO community_cache (community_name, is_active, crawl_priority, quality_tier, created_at, updated_at)
            SELECT name, true, 50, 'high', NOW(), NOW()
            FROM community_pool p
            WHERE p.is_active = true
              AND NOT EXISTS (
                  SELECT 1 FROM community_cache c WHERE c.community_name = p.name
              )
        """
        res = conn.execute(text(init_sql))
        print(f"✅ Initialized {res.rowcount} missing cache records.")
        
        # Also ensure existing cache records match is_active status
        sync_sql = """
            UPDATE community_cache c
            SET is_active = p.is_active
            FROM community_pool p
            WHERE c.community_name = p.name
              AND c.is_active != p.is_active
        """
        res_sync = conn.execute(text(sync_sql))
        print(f"🔄 Synced {res_sync.rowcount} cache status flags.")
        
        trans.commit()
        
        # 2. Audit Fields
        print("\n🧐 Auditing Cache Core Fields (207 Total)...\n")
        
        # Check Last Crawled Distribution
        never_crawled = conn.execute(text("SELECT count(*) FROM community_cache WHERE last_crawled_at IS NULL")).scalar()
        crawled_recently = conn.execute(text("SELECT count(*) FROM community_cache WHERE last_crawled_at > NOW() - INTERVAL '7 days'")).scalar()
        
        print(f"⏳ Never Crawled: {never_crawled} (New + some old?)")
        print(f"🟢 Crawled < 7d:  {crawled_recently}")
        
        # Check Watermark
        no_watermark = conn.execute(text("SELECT count(*) FROM community_cache WHERE last_seen_post_id IS NULL")).scalar()
        print(f"🌊 No Watermark:  {no_watermark} (Fresh start)")
        
        # Check Priority
        prio_stats = conn.execute(text("SELECT crawl_priority, count(*) FROM community_cache GROUP BY crawl_priority")).fetchall()
        print(f"⚡ Priority Dist: {prio_stats}")

    except Exception as e:
        trans.rollback()
        print(f"❌ Error: {e}")

    conn.close()

if __name__ == "__main__":
    init_and_audit_cache()
