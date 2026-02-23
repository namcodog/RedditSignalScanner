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

def investigate_phase2():
    db_url = load_env_config()
    if not db_url:
        return

    engine = create_engine(db_url)
    conn = engine.connect()
    print("🕵️ Starting Phase 2 Investigation (No Changes)...\n")

    # ==========================================
    # 1. Double Prefix Analysis (r/r/)
    # ==========================================
    print("=== 1. Double Prefix Infection Analysis ===")
    
    double_prefix_pool = conn.execute(text(
        "SELECT count(*), sum(case when is_active then 1 else 0 end) FROM community_pool WHERE name LIKE 'r/r/%'"
    )).fetchone()
    
    double_prefix_cache = conn.execute(text(
        "SELECT count(*) FROM community_cache WHERE community_name LIKE 'r/r/%'"
    )).scalar()
    
    double_prefix_posts = conn.execute(text(
        "SELECT count(*) FROM posts_raw WHERE subreddit LIKE 'r/r/%'"
    )).scalar()

    print(f"Community Pool (Total Infected): {double_prefix_pool[0]}")
    print(f"Community Pool (Active Infected): {double_prefix_pool[1]}")
    print(f"Community Cache Infected: {double_prefix_cache}")
    print(f"Posts Raw Infected: {double_prefix_posts}")

    # ==========================================
    # 2. Zombie Communities Analysis (The 1137)
    # ==========================================
    print("\n=== 2. Zombie Communities Analysis ===")
    
    # Get time range of zombies
    zombie_stats = conn.execute(text(
        """
        SELECT 
            min(created_at), max(created_at), 
            min(updated_at), max(updated_at)
        FROM community_pool 
        WHERE is_active = false
        """
    )).fetchone()
    
    print(f"Zombies Created Range: {zombie_stats[0]} TO {zombie_stats[1]}")
    print(f"Zombies Updated Range: {zombie_stats[2]} TO {zombie_stats[3]}")
    
    # Check if they have specific metadata in 'categories' that identifies them
    # e.g. do they all share a specific 'source'?
    zombie_sources = conn.execute(text(
        """
        SELECT categories->>'source' as src, count(*)
        FROM community_pool 
        WHERE is_active = false AND jsonb_typeof(categories) = 'object'
        GROUP BY src
        LIMIT 5
        """
    )).fetchall()
    
    if zombie_sources:
        print("Zombie Sources (from categories JSON):")
        for src, count in zombie_sources:
            print(f"  Source: {src} (Count: {count})")

    # ==========================================
    # 3. Categories Field Reality Check
    # ==========================================
    print("\n=== 3. Categories Field Reality Check (Top 129 Active) ===")
    
    # What formats exist in the active 129?
    cat_formats = conn.execute(text(
        """
        SELECT jsonb_typeof(categories) as dtype, count(*)
        FROM community_pool 
        WHERE is_active = true
        GROUP BY dtype
        """
    )).fetchall()
    
    print("Active Communities 'categories' data types:")
    for dtype, count in cat_formats:
        print(f"  Type: {dtype} (Count: {count})")
        
    # Show samples of each type
    print("\nSamples of Active Categories:")
    samples = conn.execute(text(
        "SELECT name, categories, jsonb_typeof(categories) FROM community_pool WHERE is_active = true LIMIT 10"
    )).fetchall()
    
    for row in samples:
        print(f"  {row[0]}: {row[1]} (Type: {row[2]})")

    conn.close()

if __name__ == "__main__":
    investigate_phase2()