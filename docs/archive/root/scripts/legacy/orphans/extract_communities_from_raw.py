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

def extract_from_raw():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🔍 Extracting 'Real' Communities from Raw Data (posts_raw)...\n")
    
    # 1. Aggregate from posts_raw
    # Note: Normalize subreddit names (lower case, ensure r/ prefix) just in case
    query = """
        SELECT 
            subreddit, 
            count(*) as post_count,
            max(created_at) as last_post_at
        FROM posts_raw 
        GROUP BY subreddit 
        ORDER BY post_count DESC
    """
    
    real_communities = conn.execute(text(query)).fetchall()
    print(f"Found {len(real_communities)} unique subreddits in posts_raw.\n")
    
    # 2. Check against community_pool
    # Fetch all pool names for comparison
    pool_names = set(conn.execute(text("SELECT name FROM community_pool")).scalars())
    
    # 3. Generate Report
    print(f"{ 'Subreddit':<30} | {'Posts':<10} | {'Last Post':<20} | {'In Pool?'}")
    print("-" * 80)
    
    missing_in_pool = []
    
    for row in real_communities:
        name = row[0]
        count = row[1]
        last_at = str(row[2])[:19]
        in_pool = "✅" if name in pool_names else "❌"
        
        if name not in pool_names:
            missing_in_pool.append(name)
            
        print(f"{name:<30} | {count:<10} | {last_at:<20} | {in_pool}")
        
    print("-" * 80)
    print(f"\nSummary:")
    print(f"Total Communities with Data: {len(real_communities)}")
    print(f"Communities MISSING from Pool: {len(missing_in_pool)}")
    
    if missing_in_pool:
        print("\n⚠️ The following communities have data but are NOT in the configuration pool:")
        for m in missing_in_pool:
            print(f"  - {m}")

    conn.close()

if __name__ == "__main__":
    extract_from_raw()
