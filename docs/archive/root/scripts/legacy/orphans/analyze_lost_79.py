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

def analyze_lost():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🕵️ Analyzing the 'Lost 79' (In CSV but Missing from DB)...\n")
    
    # 1. Get Current DB Active List
    db_names = set(conn.execute(text("SELECT name FROM community_pool WHERE is_active=true")).scalars())
    
    # 2. Get CSV List
    csv_path = os.path.join(os.path.dirname(__file__), '../data/community_list_check.csv')
    csv_names = set()
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader, None) # Skip header
            for row in reader:
                if row:
                    name = normalize_name(row[0])
                    if name:
                        csv_names.add(name)
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # 3. Calculate Missing
    missing = csv_names - db_names
    
    print(f"Total in CSV: {len(csv_names)}")
    print(f"Total in DB:  {len(db_names)}")
    print(f"Missing Count: {len(missing)}")
    
    print("\n=== The Missing List ===")
    for m in sorted(list(missing)):
        print(f"  - {m}")

    conn.close()

if __name__ == "__main__":
    analyze_lost()
