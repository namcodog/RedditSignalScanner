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

def restore_cache():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    trans = conn.begin()
    
    print("🔄 Restoring Cache State from Raw Data...\n")
    
    try:
        # Complex Update with Join/Subquery is tricky in SQLAlchemy text across DBs.
        # Let's do it iteratively or with a powerful CTE. Postgres supports FROM in UPDATE.
        
        # Logic:
        # For each community in cache, find max(fetched_at) and the ID associated with it.
        # Also count total posts. 
        
        query = """
            WITH latest_posts AS (
                SELECT DISTINCT ON (subreddit)
                    subreddit,
                    source_post_id,
                    fetched_at
                FROM posts_raw
                ORDER BY subreddit, fetched_at DESC
            ),
            counts AS (
                SELECT subreddit, count(*) as total
                FROM posts_raw
                GROUP BY subreddit
            )
            UPDATE community_cache c
            SET 
                last_crawled_at = lp.fetched_at,
                last_seen_post_id = lp.source_post_id,
                total_posts_fetched = cnt.total,
                updated_at = NOW()
            FROM latest_posts lp
            JOIN counts cnt ON lp.subreddit = cnt.subreddit
            WHERE c.community_name = lp.subreddit
        """
        
        res = conn.execute(text(query))
        
        trans.commit()
        print(f"✅ Successfully restored cache state for {res.rowcount} communities.")
        
        # Verify results
        print("\n=== Verification Sample ===")
        sample = conn.execute(text("""
            SELECT community_name, last_crawled_at, last_seen_post_id, total_posts_fetched 
            FROM community_cache 
            WHERE last_crawled_at IS NOT NULL 
            LIMIT 5
        """)).fetchall()
        
        for row in sample:
            print(f"  {row[0]}: Last Crawl={row[1]}, ID={row[2]}, Total={row[3]}")
            
    except Exception as e:
        trans.rollback()
        print(f"❌ Error: {e}")

    conn.close()

if __name__ == "__main__":
    restore_cache()
