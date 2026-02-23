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

def get_targets():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    targets = conn.execute(text("""
        SELECT name FROM community_pool 
        WHERE is_active=true AND description_keywords = '{}'::jsonb
        ORDER BY name
    """)).scalars().all()
    
    print(json.dumps(targets))
    conn.close()

if __name__ == "__main__":
    get_targets()
