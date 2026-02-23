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

def screen_communities():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🔍 Screening Communities based on Asset Health...\n")
    print("Criteria: > 100 posts AND Activity within last 90 days\n")

    # Calculate 90 days ago
    ninety_days_ago = datetime.now() - timedelta(days=90)
    
    query = """
        SELECT 
            subreddit, 
            count(*) as post_count, 
            max(created_at) as last_post_at
        FROM posts_raw 
        GROUP BY subreddit 
        HAVING count(*) > 100
        ORDER BY post_count DESC
    """
    
    candidates = conn.execute(text(query)).fetchall()
    
    pass_list = []
    fail_list = []
    
    print(f"{ 'Subreddit':<30} | { 'Posts':<8} | { 'Last Active':<20} | {'Status'}")
    print("-" * 80)
    
    for row in candidates:
        name = row[0]
        count = row[1]
        last_at = row[2] # timestamp object
        
        # Check Recency
        # Note: Ensure last_at is timezone aware or compatible
        if last_at.tzinfo is None:
             # Fallback if DB returns naive (though usually PG returns aware)
             pass 
        
        # Simple comparison (assuming both naive or both aware, usually works with PG driver)
        # Let's make ninety_days_ago aware if needed, or compare naive.
        # Safest is to compare dates or ignore TZ for rough check.
        
        is_recent = last_at > ninety_days_ago.replace(tzinfo=last_at.tzinfo)
        
        status = "✅ PASS" if is_recent else "❌ STALE"
        
        line = f"{name:<30} | {count:<8} | {str(last_at)[:19]:<20} | {status}"
        print(line)
        
        if is_recent:
            pass_list.append(name)
        else:
            fail_list.append(name)
            
    print("-" * 80)
    print(f"\n📊 Summary:")
    print(f"Total Candidates (>100 posts): {len(candidates)}")
    print(f"✅ Qualified (Active recently): {len(pass_list)}")
    print(f"❌ Stale (Inactive > 90 days): {len(fail_list)}")

    # Also check the "Small" ones (<100 posts) just to report count
    small_count = conn.execute(text("SELECT count(DISTINCT subreddit) FROM posts_raw GROUP BY subreddit HAVING count(*) <= 100")).rowcount
    # Wait, raw query logic for count distinct group by is tricky to get single number.
    # Better:
    small_count = conn.execute(text("SELECT count(*) FROM (SELECT subreddit FROM posts_raw GROUP BY subreddit HAVING count(*) <= 100) x")).scalar()
    print(f"⚠️ Discarded (Too small <= 100 posts): {small_count}")

    conn.close()

if __name__ == "__main__":
    screen_communities()
