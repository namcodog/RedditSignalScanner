import os
import sys
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Ensure we can import from backend
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def load_env_config():
    env_path = os.path.join(os.path.dirname(__file__), '../.env')
    load_dotenv(env_path)
    url = os.getenv('DATABASE_URL')
    if url and '+asyncpg' in url:
        return url.replace('+asyncpg', '+psycopg2')
    return url

def investigate():
    db_url = load_env_config()
    if not db_url:
        print("❌ Error: DATABASE_URL not found")
        return

    engine = create_engine(db_url)
    conn = engine.connect()
    print("🕵️ Starting Deep Investigation...\n")

    # ==========================================
    # 1. Vector Investigation
    # ==========================================
    print("=== 1. Vector Orphan Analysis ===")
    # Count total orphans (ref hot)
    orphan_hot_count = conn.execute(text(
        "SELECT count(*) FROM post_embeddings pe LEFT JOIN posts_hot ph ON pe.post_id = ph.id WHERE ph.id IS NULL"
    )).scalar()
    
    # Check if they exist in RAW (The critical check)
    # Note: posts_raw.id might not match posts_hot.id directly if IDs are generated differently.
    # Let's assume id is consistent or check linking.
    # Wait, usually raw and hot have different PKs. 
    # Let's check if we can link via source_post_id.
    # First, let's see if post_embeddings.post_id matches posts_raw.id directly.
    
    orphan_raw_count = conn.execute(text(
        "SELECT count(*) FROM post_embeddings pe LEFT JOIN posts_raw pr ON pe.post_id = pr.id WHERE pr.id IS NULL"
    )).scalar()

    print(f"Total Vectors: {conn.execute(text('SELECT count(*) FROM post_embeddings')).scalar()}")
    print(f"Vectors missing from Hot Cache: {orphan_hot_count}")
    print(f"Vectors missing from Raw Storage (True Orphans): {orphan_raw_count}")
    
    if orphan_hot_count > 0 and orphan_raw_count == 0:
        print("💡 INSIGHT: The vectors are safe! They correspond to posts in 'posts_raw' but have fallen out of 'posts_hot'.")
        print("   This confirms the architecture issue: Embeddings should probably link to Raw, not Hot.")
    elif orphan_raw_count > 0:
        print(f"⚠️ WARNING: {orphan_raw_count} vectors seem to reference IDs that don't exist in either Raw or Hot.")

    # ==========================================
    # 2. Label Structure Forensics
    # ==========================================
    print("\n=== 2. Label Structure Forensics ===")
    bad_labels = conn.execute(text(
        """
        SELECT p.id, label 
        FROM posts_hot p, jsonb_array_elements(p.content_labels) label
        WHERE NOT (label ? 'category' AND label ? 'sentiment' AND label ? 'confidence')
        LIMIT 5
        """
    )).fetchall()

    if bad_labels:
        print("Sample of MALFORMED labels:")
        for row in bad_labels:
            print(f"Post ID {row[0]}: {row[1]}")
    else:
        print("No malformed labels found in sample (maybe cleared?).")

    # ==========================================
    # 3. Community Pool Census
    # ==========================================
    print("\n=== 3. Community Pool Census ===")
    total = conn.execute(text("SELECT count(*) FROM community_pool")).scalar()
    active = conn.execute(text("SELECT count(*) FROM community_pool WHERE is_active = true")).scalar()
    inactive = conn.execute(text("SELECT count(*) FROM community_pool WHERE is_active = false")).scalar()
    
    print(f"Total Communities: {total}")
    print(f"Active: {active}")
    print(f"Inactive: {inactive}")
    
    if total != (active + inactive):
         print("⚠️ Math mismatch (NULL is_active?)")

    print("\nBreakdown by 'categories' format:")
    invalid_cats = conn.execute(text(
        "SELECT name, is_active, categories, jsonb_typeof(categories) FROM community_pool WHERE jsonb_typeof(categories) != 'array' LIMIT 5"
    )).fetchall()
    
    if invalid_cats:
        print("Sample of communities with INVALID categories:")
        for row in invalid_cats:
            print(f"r/{row[0]} (Active:{row[1]}): Type={row[3]}, Value={row[2]}")
            
    conn.close()

if __name__ == "__main__":
    investigate()
