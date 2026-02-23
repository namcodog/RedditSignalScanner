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

def audit_semantic_base():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🟣 Auditing Semantic Knowledge Base...\n")
    
    # 1. Check for potential tables
    candidates = [
        'semantic_library', 'semantic_concepts', 'keywords', 'dictionary', 
        'terms', 'entities', 'industry_terms', 'mv_analysis_entities', 'mv_analysis_labels'
    ]
    
    found_tables = []
    
    for table in candidates:
        # Special check for Materialized Views
        if table.startswith('mv_'):
            exists = conn.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM pg_matviews 
                    WHERE schemaname = 'public' AND matviewname = '{table}'
                )
            """)).scalar()
        else:
            exists = conn.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = '{table}'
                )
            """)).scalar()
        
        if exists:
            count = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()
            found_tables.append((table, count))
            print(f"✅ Found Table: {table} (Rows: {count})")
        else:
            print(f"❌ Missing Table: {table}")
            
    # 2. Check Materialized Views specifically (mv_*)
    # They might be empty if not refreshed
    
    # 3. Check for JSON dictionaries in Config
    # Sometimes dictionaries are in config tables
    
    conn.close()

if __name__ == "__main__":
    audit_semantic_base()
