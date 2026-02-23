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

def audit_fields():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🧬 Community Pool Fields Anatomy\n")
    
    # Total rows
    total = conn.execute(text("SELECT count(*) FROM community_pool")).scalar()
    print(f"Total Rows: {total}")
    
    # 1. Description Keywords
    print("\n--- 1. description_keywords ---")
    empty_desc = conn.execute(text("SELECT count(*) FROM community_pool WHERE description_keywords = '{}'::jsonb")).scalar()
    null_desc = conn.execute(text("SELECT count(*) FROM community_pool WHERE description_keywords IS NULL")).scalar()
    filled_desc = total - empty_desc - null_desc
    
    print(f"  🟢 Filled: {filled_desc} ({filled_desc/total*100:.1f}%)")
    print(f"  ⚪ Empty:  {empty_desc}")
    print(f"  ❌ Null:   {null_desc}")
    
    if filled_desc > 0:
        print("  Sample content:")
        sample = conn.execute(text("SELECT name, description_keywords FROM community_pool WHERE description_keywords != '{}'::jsonb LIMIT 3")).fetchall()
        for row in sample:
            print(f"    {row[0]}: {row[1]}")

    # 2. Semantic Quality Score
    print("\n--- 2. semantic_quality_score ---")
    default_score = conn.execute(text("SELECT count(*) FROM community_pool WHERE semantic_quality_score = 1.0")).scalar()
    zero_score = conn.execute(text("SELECT count(*) FROM community_pool WHERE semantic_quality_score = 0")).scalar()
    varied_score = total - default_score - zero_score
    
    print(f"  🟢 Varied (Real Score): {varied_score}")
    print(f"  ⚪ Default (1.0):       {default_score}")
    print(f"  ⚪ Zero (0.0):          {zero_score}")

    # 3. Categories (Re-check)
    print("\n--- 3. categories ---")
    empty_cats = conn.execute(text("SELECT count(*) FROM community_pool WHERE categories = '[]'::jsonb")).scalar()
    print(f"  ⚪ Empty Arrays: {empty_cats} ({empty_cats/total*100:.1f}%)")

    conn.close()

if __name__ == "__main__":
    audit_fields()
