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

def deep_dive():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🤿 Deep Dive into Refinery Architecture...\n")
    
    # 1. Check Hot Cache TTL Definition
    print("=== 1. Hot Cache TTL Logic ===")
    # Get column default for expires_at
    ttl_def = conn.execute(text("""
        SELECT column_default 
        FROM information_schema.columns 
        WHERE table_name = 'posts_hot' AND column_name = 'expires_at'
    """)).scalar()
    print(f"Default Expiry: {ttl_def}")
    
    # 2. Check Label Ghost in Raw
    # Do we have labels in posts_raw.metadata that are missing in posts_hot.content_labels?
    print("\n=== 2. Label Ghost Hunt ===")
    
    # Check raw metadata structure
    raw_sample = conn.execute(text("""
        SELECT metadata 
        FROM posts_raw 
        WHERE metadata IS NOT NULL AND metadata::text LIKE '%label%' 
        LIMIT 1
    """ )).fetchone()
    
    if raw_sample:
        print(f"Found trace of labels in Raw Metadata: {str(raw_sample[0])[:100]}...")
    else:
        print("No trace of 'label' found in Raw Metadata json.")
        
    # Check if Hot table content_labels is just empty or NULL
    null_labels = conn.execute(text("SELECT count(*) FROM posts_hot WHERE content_labels IS NULL")).scalar()
    empty_labels = conn.execute(text("SELECT count(*) FROM posts_hot WHERE content_labels = '[]'::jsonb")).scalar()
    print(f"Hot Null Labels: {null_labels}")
    print(f"Hot Empty Labels: {empty_labels}")

    # 3. Vector FK Definition
    print("\n=== 3. Vector Alignment Definition ===")
    # Check FK constraint
    fk_def = conn.execute(text("""
        SELECT 
            tc.constraint_name, 
            kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name 
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
        WHERE tc.table_name = 'post_embeddings' AND tc.constraint_type = 'FOREIGN KEY'
    """)).fetchall()
    
    if fk_def:
        for row in fk_def:
            print(f"Constraint: {row[0]}")
            print(f"  Column: {row[1]} -> Refers to: {row[2]}.{row[3]}")
            if row[2] == 'posts_raw':
                print("  ✅ CONFIRMED: Aligned to Posts Raw (Cold Storage)")
            elif row[2] == 'posts_hot':
                print("  ❌ ALERT: Aligned to Posts Hot (Temporary Cache)!")
    else:
        print("⚠️ No Foreign Key found on post_embeddings. Checking data correlation...")
        # Data check
        raw_match = conn.execute(text("SELECT count(*) FROM post_embeddings pe JOIN posts_raw pr ON pe.post_id = pr.id")).scalar()
        hot_match = conn.execute(text("SELECT count(*) FROM post_embeddings pe JOIN posts_hot ph ON pe.post_id = ph.id")).scalar()
        print(f"  Matches in Raw: {raw_match}")
        print(f"  Matches in Hot: {hot_match}")
        
        if raw_match > 0 and hot_match == 0:
             print("  ✅ Implicit Alignment: Data matches Raw IDs, not Hot IDs.")

    conn.close()

if __name__ == "__main__":
    deep_dive()
