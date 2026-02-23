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

def list_tables():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🗺️ Listing ALL Tables in Database...\n")
    
    tables = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    """ )).scalars().all()
    
    for t in tables:
        # Count rows for context
        try:
            count = conn.execute(text(f"SELECT count(*) FROM {t}")).scalar()
            print(f"📄 {t} ({count} rows)")
        except:
            print(f"📄 {t} (Row count error)")

    conn.close()

if __name__ == "__main__":
    list_tables()
