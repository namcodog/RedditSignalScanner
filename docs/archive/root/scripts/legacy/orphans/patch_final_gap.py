import os
import sys
import json
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

def patch_final_gap():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🩹 Patching the final 17 untagged communities -> Ecommerce_Business...\n")
    
    # Update ALL remaining active communities with empty categories to 'Ecommerce_Business'
    # This is safe because we manually inspected the list and they are all business/ecommerce related.
    res = conn.execute(text("""
        UPDATE community_pool
        SET categories = '[" Ecommerce_Business"]'::jsonb
        WHERE is_active = true 
          AND categories = '[]'::jsonb
    """))
    
    conn.commit()
    print(f"✅ Patched {res.rowcount} communities.")
    
    conn.close()

if __name__ == "__main__":
    patch_final_gap()
