import os
import sys
from datetime import datetime, timedelta
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

def execute_purge():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    trans = conn.begin()
    
    print("⚔️ STARTING THE FINAL PURGE AND REBUILD...\n")
    
    try:
        # 1. Identify Lists Again (To be safe and atomic)
        cutoff_date = datetime.now() - timedelta(days=60)
        query = """
            SELECT 
                subreddit, 
                count(*) as posts_60d, 
                sum(score + num_comments) as interactions_60d
            FROM posts_raw 
            WHERE created_at > :cutoff
            GROUP BY subreddit 
        """
        results = conn.execute(text(query), {"cutoff": cutoff_date}).fetchall()
        
        survivors = set()
        victims = set()
        
        for row in results:
            name = row[0]
            p_count = row[1]
            i_count = int(row[2]) if row[2] else 0
            avg_i = round(i_count / p_count, 1) if p_count > 0 else 0
            
            if avg_i >= 20 or i_count >= 1000:
                survivors.add(name)
            else:
                victims.add(name)
        
        print(f"🎯 Targets Locked: {len(survivors)} Survivors, {len(victims)} Victims")

        # FIX SEQUENCE: Ensure ID sequence is synced with max ID
        print("🔧 Fixing ID sequence...")
        conn.execute(text("SELECT setval('community_pool_id_seq', COALESCE((SELECT MAX(id) FROM community_pool), 0) + 1, false)"))
        
        # 2. Update Pool for Survivors
        print("\n=== 1. Securing Survivors in Pool ===")
        # Use a loop for safety and clarity, or bulk insert. 
        # Given 120 items, loop is fine and easier to debug.
        updated_count = 0
        for name in survivors:
            # Robust Upsert: Try Update first
            update_sql = """
                UPDATE community_pool 
                SET is_active = true, 
                    tier = 'high',
                    updated_at = NOW()
                WHERE name = :name
            """
            res = conn.execute(text(update_sql), {"name": name})
            
            if res.rowcount == 0:
                # Insert if not exists
                insert_sql = """
                    INSERT INTO community_pool (name, is_active, tier, categories, description_keywords, created_at, updated_at, semantic_quality_score)
                    VALUES (:name, true, 'high', '[]'::jsonb, '{}'::jsonb, NOW(), NOW(), 1.0)
                """
                conn.execute(text(insert_sql), {"name": name})
            
            updated_count += 1
        print(f"✅ Secured {updated_count} communities in Pool.")

        # 3. Deactivate Victims in Pool
        print("\n=== 2. Deactivating Victims in Pool ===")
        if victims:
            conn.execute(text("UPDATE community_pool SET is_active = false WHERE name IN :names"), {"names": tuple(victims)})
            print(f"✅ Deactivated {len(victims)} communities in Pool.")
        
        # 4. The Physical Purge
        print("\n=== 3. Physical Data Purge (This may take a moment) ===")
        
        # 4.1 Delete Posts Raw
        # Note: We need to delete ALL posts for victims, not just recent ones.
        # We delete based on the VICTIM LIST derived from recent data.
        if victims:
            print("  - Deleting from posts_raw...")
            del_posts = conn.execute(text("DELETE FROM posts_raw WHERE subreddit IN :names"), {"names": tuple(victims)})
            print(f"    🗑️ Deleted {del_posts.rowcount} rows from posts_raw")
            
            # 4.2 Delete Comments (Cascade usually handles this if FK exists, but let's be explicit if not)
            # Efficient way: Delete comments where post_id not in posts_raw anymore?
            # Or delete by subreddit if comments have subreddit column (they do!)
            print("  - Deleting from comments...")
            del_comments = conn.execute(text("DELETE FROM comments WHERE subreddit IN :names"), {"names": tuple(victims)})
            print(f"    🗑️ Deleted {del_comments.rowcount} rows from comments")

            # 4.3 Delete Hot Cache
            print("  - Deleting from posts_hot...")
            del_hot = conn.execute(text("DELETE FROM posts_hot WHERE subreddit IN :names"), {"names": tuple(victims)})
            print(f"    🗑️ Deleted {del_hot.rowcount} rows from posts_hot")
            
            # 4.4 Delete Community Cache
            print("  - Deleting from community_cache...")
            del_cache = conn.execute(text("DELETE FROM community_cache WHERE community_name IN :names"), {"names": tuple(victims)})
            print(f"    🗑️ Deleted {del_cache.rowcount} rows from community_cache")

        # 5. Final Cleanup: Identify communities in posts_raw that were NOT in our screen list at all (inactive > 60d)
        # These are the "Old Zombies" we saw earlier (stale for years).
        # They weren't in 'results' because they had no posts > 60d.
        # We should purge them too to fully align with the "120 Survivors" baseline.
        print("\n=== 4. Cleaning Ancient Zombies (Inactive > 60d) ===")
        # Any subreddit in posts_raw that is NOT in survivors set must go.
        print("  - Identifying ancient zombies...")
        
        # Get list of ALL subreddits currently in raw (after above delete)
        remaining_subs = set(conn.execute(text("SELECT DISTINCT subreddit FROM posts_raw")).scalars())
        ancient_victims = remaining_subs - survivors
        
        if ancient_victims:
            print(f"  - Found {len(ancient_victims)} ancient zombies (e.g. {list(ancient_victims)[:3]}). Purging...")
            
            conn.execute(text("DELETE FROM posts_raw WHERE subreddit IN :names"), {"names": tuple(ancient_victims)})
            conn.execute(text("DELETE FROM comments WHERE subreddit IN :names"), {"names": tuple(ancient_victims)})
            # Also deactivate in pool if present
            conn.execute(text("UPDATE community_pool SET is_active = false WHERE name IN :names"), {"names": tuple(ancient_victims)})
            
            print(f"    🗑️ Purged ancient data for {len(ancient_victims)} communities.")
        else:
            print("  - No ancient zombies found.")

        trans.commit()
        print("\n✨ PURGE COMPLETE. Baseline Restored.")
        
    except Exception as e:
        trans.rollback()
        print(f"\n❌ CRITICAL ERROR: {e}")
        print("🔄 Rolled back changes.")

    conn.close()

if __name__ == "__main__":
    execute_purge()
