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

def audit_cache():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🕸️ Community Cache Consistency Check\n")
    
    # 1. Get Sets
    pool_active = set(conn.execute(text("SELECT name FROM community_pool WHERE is_active = true")).scalars())
    cache_all = set(conn.execute(text("SELECT community_name FROM community_cache")).scalars())
    
    print(f"Pool Active: {len(pool_active)}")
    print(f"Cache Total: {len(cache_all)}")
    
    # 2. Compare
    missing_in_cache = pool_active - cache_all
    orphan_in_cache = cache_all - pool_active
    
    print(f"\n✅ Aligned: {len(pool_active.intersection(cache_all))}")
    
    print(f"\n⚠️ Missing in Cache (Need Init): {len(missing_in_cache)}")
    if missing_in_cache:
        print(f"  Example: {list(missing_in_cache)[:3]}")
        
    print(f"\n🗑️ Orphan in Cache (Need Delete): {len(orphan_in_cache)}")
    if orphan_in_cache:
        print(f"  Example: {list(orphan_in_cache)[:3]}")

    conn.close()

if __name__ == "__main__":
    audit_cache()
