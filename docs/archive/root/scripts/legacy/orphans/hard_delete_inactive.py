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

def hard_delete_inactive():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    trans = conn.begin()
    
    print("🧹 STARTING HARD DELETE OF INACTIVE COMMUNITIES...\n")
    
    try:
        # 1. Identify Targets
        # Get IDs/Names of inactive communities
        targets = conn.execute(text("SELECT name FROM community_pool WHERE is_active = false")).scalars().all()
        
        if not targets:
            print("✅ No inactive communities found. System is already clean.")
            return

        print(f"🎯 Targets Identified: {len(targets)} inactive communities to obliterate.")
        
        target_tuple = tuple(targets)

        # 2. Cascade Delete
        # We delete from dependent tables first, just to be thorough, 
        # although CASCADING FKs might handle some.
        
        print("  - Deleting from posts_raw (residue)...")
        res_posts = conn.execute(text("DELETE FROM posts_raw WHERE subreddit IN :names"), {"names": target_tuple})
        print(f"    🗑️ Deleted {res_posts.rowcount} rows.")

        print("  - Deleting from comments (residue)...")
        res_comments = conn.execute(text("DELETE FROM comments WHERE subreddit IN :names"), {"names": target_tuple})
        print(f"    🗑️ Deleted {res_comments.rowcount} rows.")

        print("  - Deleting from posts_hot (residue)...")
        res_hot = conn.execute(text("DELETE FROM posts_hot WHERE subreddit IN :names"), {"names": target_tuple})
        print(f"    🗑️ Deleted {res_hot.rowcount} rows.")

        print("  - Deleting from community_cache...")
        res_cache = conn.execute(text("DELETE FROM community_cache WHERE community_name IN :names"), {"names": target_tuple})
        print(f"    🗑️ Deleted {res_cache.rowcount} rows.")

        # 3. Final Kill: community_pool
        print("  - Deleting from community_pool...")
        res_pool = conn.execute(text("DELETE FROM community_pool WHERE is_active = false"))
        print(f"    💀 DESTROYED {res_pool.rowcount} communities.")
        
        trans.commit()
        print("\n✨ CLEANUP COMPLETE. No trace left.")
        
    except Exception as e:
        trans.rollback()
        print(f"\n❌ CRITICAL ERROR: {e}")
        print("🔄 Rolled back changes.")

    conn.close()

if __name__ == "__main__":
    hard_delete_inactive()
