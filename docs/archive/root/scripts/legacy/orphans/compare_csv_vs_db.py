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
    """Ensure r/ prefix and lowercase"""
    if not name: return ""
    name = name.strip().lower()
    if not name.startswith('r/'):
        return f"r/{name}"
    return name

def compare_lists():
    # 1. Load DB List (The 120 Survivors)
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("📊 Comparing CSV vs Database...\n")
    
    # Only select the ACTIVE ones we just finalized
    db_communities = set(conn.execute(text("SELECT name FROM community_pool WHERE is_active = true")).scalars())
    print(f"Database Active Count: {len(db_communities)}")

    # 2. Load CSV List
    csv_path = os.path.join(os.path.dirname(__file__), '../data/community_list_check.csv')
    csv_communities = set()
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f: # sig to handle BOM
            # Try to sniff header or just assume first column
            reader = csv.reader(f)
            header = next(reader, None) # Skip header if it looks like one
            
            # Simple heuristic: if first cell is 'community' or 'name', skip. 
            # If it looks like data, process it.
            # Actually, let's just normalize everything.
            
            # Reset file pointer to verify header manually if needed, but let's iterate.
            # Assuming column 0 is the name.
            if header:
                # Check if header is indeed a header
                first_cell = normalize_name(header[0])
                if 'name' in first_cell or 'community' in first_cell:
                    pass # It was a header
                else:
                    csv_communities.add(first_cell) # It was data
            
            for row in reader:
                if row:
                    name = normalize_name(row[0])
                    if name:
                        csv_communities.add(name)
                        
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    print(f"CSV List Count: {len(csv_communities)}")
    
    # 3. The Comparison
    in_both = db_communities.intersection(csv_communities)
    db_only = db_communities - csv_communities
    csv_only = csv_communities - db_communities
    
    # 4. Report
    print("\n=== 1. ✅ In Both (Aligned) ===")
    print(f"Count: {len(in_both)}")
    # print(sorted(list(in_both)))

    print("\n=== 2. 💎 Database Only (Hidden Gems) ===")
    print(f"Count: {len(db_only)}")
    print("These are active in DB but missing from your CSV:")
    for name in sorted(list(db_only)):
        print(f"  - {name}")

    print("\n=== 3. 🚀 CSV Only (Potential New Targets) ===")
    print(f"Count: {len(csv_only)}")
    print("These are in your CSV but NOT active in DB:")
    for name in sorted(list(csv_only)):
        print(f"  - {name}")

    conn.close()

if __name__ == "__main__":
    compare_lists()
