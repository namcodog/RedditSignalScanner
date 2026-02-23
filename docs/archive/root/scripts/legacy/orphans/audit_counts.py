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

def audit_counts():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🧮 Counting Heads (Audit)...")

    # 1. DB Stats
    total_pool = conn.execute(text("SELECT count(*) FROM community_pool")).scalar()
    active_pool = conn.execute(text("SELECT count(*) FROM community_pool WHERE is_active=true")).scalar()
    inactive_pool = conn.execute(text("SELECT count(*) FROM community_pool WHERE is_active=false")).scalar()
    
    print(f"=== Database (community_pool) ===")
    print(f"Total Rows: {total_pool}")
    print(f"  - Active:   {active_pool}")
    print(f"  - Inactive: {inactive_pool}")
    
    # 2. CSV Stats
    csv_path = os.path.join(os.path.dirname(__file__), '../data/community_list_check.csv')
    csv_names = set()
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                name = normalize_name(row[0])
                if name and name != 'r/community': # skip header
                    csv_names.add(name)
    
    print(f"\n=== CSV File ===")
    print(f"Unique Names: {len(csv_names)}")
    
    # 3. Cross Check
    # Names in CSV but NOT in Pool (Should be 0 if merge worked)
    db_names = set(conn.execute(text("SELECT name FROM community_pool")).scalars())
    missing_from_db = csv_names - db_names
    
    print(f"\n=== Reconciliation ===")
    print(f"Missing from DB (CSV - DB): {len(missing_from_db)}")
    if missing_from_db:
        print(f"  Example Missing: {list(missing_from_db)[:3]}")
        
    # Names in CSV that are INACTIVE in DB
    # These are the ones we "Skipped" but maybe you wanted to "Activate"
    inactive_names = set(conn.execute(text("SELECT name FROM community_pool WHERE is_active=false")).scalars())
    csv_but_inactive = csv_names.intersection(inactive_names)
    
    print(f"In CSV but Inactive in DB: {len(csv_but_inactive)}")
    print(f"  (These {len(csv_but_inactive)} communities were skipped because they exist, but are disabled)")
    
    conn.close()

if __name__ == "__main__":
    audit_counts()
