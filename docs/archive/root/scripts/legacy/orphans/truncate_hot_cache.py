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

def truncate_hot():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    trans = conn.begin()
    
    print("🔥 TRUNCATING HOT CACHE (posts_hot)...")
    
    try:
        # Truncate is faster and reclaims space immediately
        # CASCADE is needed if other tables ref it (like content_entities maybe?)
        conn.execute(text("TRUNCATE TABLE posts_hot CASCADE"))
        
        trans.commit()
        print("✅ Hot Cache Flushed. Ready for fresh data.")
        
    except Exception as e:
        trans.rollback()
        print(f"❌ Error: {e}")

    conn.close()

if __name__ == "__main__":
    truncate_hot()
