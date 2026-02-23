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

def screen_final_cut():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("⚔️ Executing 'The Final Cut' Analysis (PREVIEW ONLY)...")
    
    cutoff_date = datetime.now() - timedelta(days=60)
    
    # Base metrics query
    query = """
        SELECT 
            subreddit, 
            count(*) as posts_60d, 
            sum(score + num_comments) as interactions_60d
        FROM posts_raw 
        WHERE created_at > :cutoff
        GROUP BY subreddit 
        ORDER BY interactions_60d DESC
    """
    
    results = conn.execute(text(query), {"cutoff": cutoff_date}).fetchall()
    
    survivors = []
    victims = []
    
    for row in results:
        name = row[0]
        p_count = row[1]
        i_count = int(row[2]) if row[2] else 0
        avg_i = round(i_count / p_count, 1) if p_count > 0 else 0
        
        # The Logic: Keep if (Avg >= 20) OR (Total >= 1000)
        is_high_quality = avg_i >= 20
        is_big_volume = i_count >= 1000
        
        # Decision
        if is_high_quality or is_big_volume:
            reason = "High Quality" if is_high_quality else "Big Volume"
            if is_high_quality and is_big_volume: reason = "Star Performer"
            
            survivors.append({
                "name": name,
                "posts": p_count,
                "interactions": i_count,
                "avg": avg_i,
                "reason": reason
            })
        else:
            victims.append({
                "name": name,
                "posts": p_count,
                "interactions": i_count,
                "avg": avg_i
            })
            
    # Print Survivors
    print(f"✅ SURVIVORS (Proposed to KEEP) - Count: {len(survivors)}")
    print(f"{ 'Subreddit':<30} | {'Posts':<6} | {'Interactions':<12} | {'Avg':<6} | {'Reason'}")
    print("-" * 85)
    for s in survivors:
        print(f"{s['name']:<30} | {s['posts']:<6} | {s['interactions']:<12} | {s['avg']:<6} | {s['reason']}")
        
    print("\n" + "="*85 + "\n")
    
    # Print Victims
    print(f"❌ VICTIMS (Proposed to PURGE) - Count: {len(victims)}")
    print(f"{ 'Subreddit':<30} | {'Posts':<6} | {'Interactions':<12} | {'Avg':<6} | {'Reason'}")
    print("-" * 85)
    for v in victims:
        print(f"{v['name']:<30} | {v['posts']:<6} | {v['interactions']:<12} | {v['avg']:<6} | Low Quality & Low Volume")

    conn.close()

if __name__ == "__main__":
    screen_final_cut()
