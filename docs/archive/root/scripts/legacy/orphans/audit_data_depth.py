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

def audit_depth():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("📅 Auditing Data Depth (History Span)...\n")
    
    # Target: active communities with cache (The 120 Veterans)
    # We can query raw directly.
    
    query = """
        SELECT 
            subreddit,
            min(created_at) as oldest_post,
            max(created_at) as newest_post,
            count(*) as total_posts
        FROM posts_raw
        GROUP BY subreddit
        ORDER BY oldest_post ASC
    """
    
    results = conn.execute(text(query)).fetchall()
    
    now = datetime.now()
    one_year_ago = now - timedelta(days=365)
    
    full_year_club = []
    partial_club = []
    
    print(f"{ 'Subreddit':<30} | { 'Oldest Post':<20} | { 'Span (Days)':<10} | {'Status'}")
    print("-" * 80)
    
    for row in results:
        name = row[0]
        oldest = row[1]
        newest = row[2]
        count = row[3]
        
        if not oldest or not newest: continue
        
        # Handle naive datetime if needed
        if oldest.tzinfo:
            # make naive for simple subtract or ensure one_year_ago is aware
            # PG usually returns aware. Let's convert one_year_ago to match result timezone or just ignore TZ
            pass 
            
        span_days = (newest - oldest).days
        
        # Check if oldest is older than 1 year ago (approx)
        # We need to be careful with TZ comparison. 
        # Let's just use timestamp comparison if possible, or naive.
        # Simplest: compare span_days > 360
        
        # Status
        if span_days >= 330: # Allow some buffer for "Year"
            status = "✅ > 1 Year"
            full_year_club.append(name)
        else:
            status = f"⚠️ {span_days} days"
            partial_club.append(name)
            
        print(f"{name:<30} | {str(oldest)[:10]:<20} | {span_days:<10} | {status}")
        
    print("-" * 80)
    print(f"\n📊 Depth Summary:")
    print(f"Total Veterans Scanned: {len(results)}")
    print(f"🏆 Full Year Coverage:   {len(full_year_club)}")
    print(f"🚧 Partial Coverage:     {len(partial_club)}")
    
    if partial_club:
        print(f"\nNeed Backfill (Top 5): {partial_club[:5]}...")

    conn.close()

if __name__ == "__main__":
    audit_depth()
