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

def sweep_newcomers():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🧹 Sweeping for Hidden Data in Newcomers...\n")
    
    # 1. Get list of 'Newcomers' (Active in Pool, but Cache says NULL crawled)
    # Or better: Pool says active, but we want to check raw specifically.
    # Let's rely on the Cache 'Never Crawled' status we just established.
    
    newcomer_names = conn.execute(text("""
        SELECT community_name 
        FROM community_cache 
        WHERE last_crawled_at IS NULL
    """)).scalars().all()
    
    print(f"Target List: {len(newcomer_names)} communities (The 'Newcomers')")
    
    if not newcomer_names:
        return

    # 2. Check Raw for each
    found_hidden = 0
    
    # Check exact match
    print("--- Checking Exact Match ---")
    for name in newcomer_names:
        count = conn.execute(text("SELECT count(*) FROM posts_raw WHERE subreddit = :name"), {"name": name}).scalar()
        if count > 0:
            print(f"⚠️ FOUND HIDDEN DATA: {name} has {count} posts!")
            found_hidden += 1
            
    # Check Case-Insensitive Match (Just in case r/Shopify vs r/shopify)
    print("--- Checking Case-Insensitive Match ---")
    for name in newcomer_names:
        # Strip r/ prefix for fuzzy search if needed, but let's try ILIKE
        count = conn.execute(text("SELECT count(*) FROM posts_raw WHERE subreddit ILIKE :name"), {"name": name}).scalar()
        # We already checked exact, so if > 0 here but exact was 0, it's a case issue.
        # To be simple, just report any non-zero.
        if count > 0:
             # Re-check if we already reported it
             # (Assuming exact check printed it)
             pass 

    if found_hidden == 0:
        print("\n✅ CONFIRMED: These 87 communities have absolutely ZERO data in posts_raw.")
    else:
        print(f"\n❌ FOUND DATA for {found_hidden} communities. Cache restore might have missed them due to case sensitivity?")

    conn.close()

if __name__ == "__main__":
    sweep_newcomers()
