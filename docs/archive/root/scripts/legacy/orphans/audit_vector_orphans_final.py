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

def audit_vectors():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🧬 Auditing Vector Embeddings Consistency...\n")
    
    # 1. Total Vectors
    total = conn.execute(text("SELECT count(*) FROM post_embeddings")).scalar()
    print(f"Total Vectors: {total}")
    
    # 2. Check for Orphans (No corresponding Raw Post)
    orphan_count = conn.execute(text("""
        SELECT count(*) 
        FROM post_embeddings pe 
        LEFT JOIN posts_raw pr ON pe.post_id = pr.id 
        WHERE pr.id IS NULL
    """)).scalar()
    
    print(f"Orphan Vectors (Target deleted): {orphan_count}")
    
    if orphan_count > 0:
        print("⚠️ Found residue from Purge operation. Cleaning up...")
        trans = conn.begin()
        try:
            # Efficient delete using subquery or join logic logic depending on DB ver
            # Simple subquery is safest across versions
            del_res = conn.execute(text("""
                DELETE FROM post_embeddings 
                WHERE post_id NOT IN (SELECT id FROM posts_raw)
            """))
            trans.commit()
            print(f"✅ Deleted {del_res.rowcount} orphan vectors.")
        except Exception as e:
            trans.rollback()
            print(f"❌ Cleanup failed: {e}")
    else:
        print("✅ Vector store is clean. Cascade delete likely worked.")

    conn.close()

if __name__ == "__main__":
    audit_vectors()
