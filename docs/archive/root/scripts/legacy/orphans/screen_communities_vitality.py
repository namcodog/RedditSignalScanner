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

def screen_vitality():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🔥 Screening Communities for 60-Day Vitality...\n")
    
    # Calculate 60 days ago
    cutoff_date = datetime.now() - timedelta(days=60)
    
    # Query: 
    # Filter posts created > 60 days ago
    # Aggregates: Post Count, Interaction Count (Sum of Score + Num_Comments)
    query = """
        SELECT 
            subreddit, 
            count(*) as posts_60d, 
            sum(score + num_comments) as interactions_60d,
            max(created_at) as last_active_at
        FROM posts_raw 
        WHERE created_at > :cutoff
        GROUP BY subreddit 
        ORDER BY interactions_60d DESC
    """
    
    results = conn.execute(text(query), {"cutoff": cutoff_date}).fetchall()
    
    print(f"{ 'Subreddit':<30} | {'Posts(60d)':<10} | {'Interactions(60d)':<18} | {'Avg Inter/Post':<15}")
    print("-" * 85)
    
    total_posts = 0
    total_interactions = 0
    active_comms = 0
    
    for row in results:
        name = row[0]
        p_count = row[1]
        i_count = int(row[2]) if row[2] else 0
        
        # Simple metric: Average interaction per post
        avg_i = round(i_count / p_count, 1) if p_count > 0 else 0
        
        print(f"{name:<30} | {p_count:<10} | {i_count:<18} | {avg_i:<15}")
        
        total_posts += p_count
        total_interactions += i_count
        active_comms += 1
            
    print("-" * 85)
    print(f"\n📊 Summary (Last 60 Days):")
    print(f"Total Active Communities: {active_comms}")
    print(f"Total Posts Generated: {total_posts}")
    print(f"Total User Interactions: {total_interactions}")

    conn.close()

if __name__ == "__main__":
    screen_vitality()
