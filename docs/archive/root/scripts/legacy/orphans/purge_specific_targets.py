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

def purge_specific():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    trans = conn.begin()
    
    targets = ('r/commit', 'r/subreddit')
    
    print(f"🗑️ Purging specific targets: {targets}..\n")
    
    try:
        # 1. Delete from Pool
        res_pool = conn.execute(text("DELETE FROM community_pool WHERE name IN :names"), {"names": targets})
        print(f"  - Pool: Deleted {res_pool.rowcount} rows")
        
        # 2. Delete from Cache
        res_cache = conn.execute(text("DELETE FROM community_cache WHERE community_name IN :names"), {"names": targets})
        print(f"  - Cache: Deleted {res_cache.rowcount} rows")
        
        # 3. Delete from Data (Raw/Hot/Comments)
        res_raw = conn.execute(text("DELETE FROM posts_raw WHERE subreddit IN :names"), {"names": targets})
        print(f"  - Posts Raw: Deleted {res_raw.rowcount} rows")
        
        res_hot = conn.execute(text("DELETE FROM posts_hot WHERE subreddit IN :names"), {"names": targets})
        print(f"  - Posts Hot: Deleted {res_hot.rowcount} rows")
        
        res_comments = conn.execute(text("DELETE FROM comments WHERE subreddit IN :names"), {"names": targets})
        print(f"  - Comments: Deleted {res_comments.rowcount} rows")
        
        trans.commit()
        print("\n✅ Purge Successful.")
        
    except Exception as e:
        trans.rollback()
        print(f"❌ Error: {e}")

    conn.close()

if __name__ == "__main__":
    purge_specific()
