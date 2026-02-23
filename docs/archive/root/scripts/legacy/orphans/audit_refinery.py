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

def audit_refinery():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🔴 Auditing The Refinery (Hot Data & Intelligence)...\n")
    
    # 1. Hot Cache Status
    print("=== 1. Hot Cache Status ===")
    hot_total = conn.execute(text("SELECT count(*) FROM posts_hot")).scalar()
    print(f"Total Hot Posts: {hot_total}")
    
    # Check for Orphan Hot Posts (Subreddit not in Pool)
    orphan_hot = conn.execute(text("""
        SELECT count(*) FROM posts_hot 
        WHERE subreddit NOT IN (SELECT name FROM community_pool WHERE is_active=true)
    """)).scalar()
    print(f"Orphan Hot Posts (Invalid Community): {orphan_hot}")
    
    # Check Expiry
    expired_hot = conn.execute(text("SELECT count(*) FROM posts_hot WHERE expires_at < NOW()")).scalar()
    print(f"Expired Hot Posts: {expired_hot} (Should be purged ideally)")

    # 2. Label Health
    print("\n=== 2. Content Labels Health ===")
    # Check for broken JSON structure
    # We look for labels that are NOT null but missing key fields
    bad_labels = conn.execute(text("""
        SELECT count(*) 
        FROM posts_hot p, jsonb_array_elements(p.content_labels) label
        WHERE NOT (label ? 'category' AND label ? 'sentiment' AND label ? 'confidence')
    """,
    )).scalar()
    print(f"Malformed Labels: {bad_labels} (Should be 0 after our fix)")
    
    # Check for missing labels entirely
    no_labels = conn.execute(text("SELECT count(*) FROM posts_hot WHERE content_labels IS NULL OR content_labels = '[]'::jsonb")).scalar()
    print(f"Untagged Hot Posts: {no_labels} (Waiting for LLM Analysis)")

    # 3. Vector Embeddings Alignment
    print("\n=== 3. Vector Embeddings Alignment ===")
    vector_total = conn.execute(text("SELECT count(*) FROM post_embeddings")).scalar()
    print(f"Total Vectors: {vector_total}")
    
    # Vectors pointing to non-existent RAW posts (The Real Orphans)
    # Note: We decided Vectors link to RAW, not HOT.
    orphan_vectors = conn.execute(text("""
        SELECT count(*) 
        FROM post_embeddings pe 
        LEFT JOIN posts_raw pr ON pe.post_id = pr.id 
        WHERE pr.id IS NULL
    """,
    )).scalar()
    
    print(f"True Orphan Vectors (No Raw Post): {orphan_vectors}")
    
    # 4. Consistency Check
    # Do we have vectors for posts that are NOT in Hot? (Normal, as Hot is cache)
    # But do we have Hot posts without Vectors? (Pending embedding)
    hot_no_vector = conn.execute(text("""
        SELECT count(*) 
        FROM posts_hot ph 
        LEFT JOIN post_embeddings pe ON ph.id = pe.post_id 
        WHERE pe.post_id IS NULL
    """,
    )).scalar()
    print(f"Hot Posts Missing Vectors: {hot_no_vector}")

    conn.close()

if __name__ == "__main__":
    audit_refinery()
