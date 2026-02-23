import os
import sys
import csv
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

def normalize_name(name):
    if not name: return ""
    name = name.strip().lower()
    if not name.startswith('r/'):
        return f"r/{name}"
    return name

def merge_csv():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🔄 Merging CSV communities into Database...\n")
    
    # 1. Load CSV
    csv_path = os.path.join(os.path.dirname(__file__), '../data/community_list_check.csv')
    new_communities = set()
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            
            for row in reader:
                if row:
                    name = normalize_name(row[0])
                    if name:
                        new_communities.add(name)
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    print(f"CSV Source Count: {len(new_communities)}")
    
    # 2. Merge Logic
    added_count = 0
    skipped_count = 0
    
    # Fix sequence just in case
    conn.execute(text("SELECT setval('community_pool_id_seq', COALESCE((SELECT MAX(id) FROM community_pool), 0) + 1, false)"))

    for name in new_communities:
        # Robust Upsert: If exists, DO NOTHING (Keep existing config). If not, INSERT.
        # Check existence first
        exists = conn.execute(text("SELECT 1 FROM community_pool WHERE name = :name"), {"name": name}).scalar()
        
        if exists:
            skipped_count += 1
        else:
            # Insert New
            insert_sql = """
                INSERT INTO community_pool (name, is_active, tier, categories, description_keywords, created_at, updated_at, semantic_quality_score)
                VALUES (:name, true, 'high', '[]'::jsonb, '{}'::jsonb, NOW(), NOW(), 1.0)
            """
            conn.execute(text(insert_sql), {"name": name})
            added_count += 1
            
    conn.commit()
    print(f"✅ Merge Complete.")
    print(f"   - Added New: {added_count}")
    print(f"   - Skipped Existing: {skipped_count}")
    print(f"   - Total in Pool: {skipped_count + added_count}") # Approximation

    conn.close()

if __name__ == "__main__":
    merge_csv()
