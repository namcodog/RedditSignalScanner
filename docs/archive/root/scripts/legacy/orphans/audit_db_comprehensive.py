import os
import sys
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Ensure we can import from backend
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def load_env_config():
    """Load database URL and ensure sync driver"""
    env_path = os.path.join(os.path.dirname(__file__), '../.env')
    load_dotenv(env_path)
    url = os.getenv('DATABASE_URL')
    if url and '+asyncpg' in url:
        return url.replace('+asyncpg', '+psycopg2')
    return url

def run_comprehensive_audit():
    db_url = load_env_config()
    if not db_url:
        print("❌ Error: DATABASE_URL not found")
        return

    try:
        engine = create_engine(db_url)
        conn = engine.connect()
        print("🔍 Starting Comprehensive Database System Audit...\n")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    issues_found = []
    warnings = []

    def check(name, query, validator, severity="ERROR"):
        try:
            result = conn.execute(text(query)).fetchall()
            msg = validator(result)
            if msg:
                if severity == "ERROR":
                    issues_found.append(f"[{name}] {msg}")
                else:
                    warnings.append(f"[{name}] {msg}")
            else:
                print(f"✅ {name}")
        except Exception as e:
            issues_found.append(f"[{name}] Execution Error: {str(e)}")

    # ==========================================
    # 1. Structural & Integrity (Relationship)
    # ==========================================
    
    # Check 1.1: Orphaned Comments (Referencing non-existent posts)
    check(
        "Orphaned Comments",
        "SELECT count(*) FROM comments c LEFT JOIN posts_raw p ON c.post_id = p.id WHERE p.id IS NULL",
        lambda res: f"Found {res[0][0]} orphaned comments" if res[0][0] > 0 else None
    )

    # Check 1.2: Orphaned Embeddings
    check(
        "Orphaned Embeddings",
        "SELECT count(*) FROM post_embeddings pe LEFT JOIN posts_hot ph ON pe.post_id = ph.id WHERE ph.id IS NULL",
        lambda res: f"Found {res[0][0]} embeddings pointing to non-existent hot posts" if res[0][0] > 0 else None
    )

    # Check 1.3: Potential Missing Foreign Keys (Heuristic: columns ending in _id)
    # This is a soft check, just looking for suspicious columns
    check(
        "Suspicious Missing FKs",
        """
        SELECT table_name, column_name 
        FROM information_schema.columns 
        WHERE column_name LIKE '%_id' 
          AND table_schema = 'public'
          AND table_name NOT IN ('alembic_version', 'spatial_ref_sys')
          AND (table_name, column_name) NOT IN (
            SELECT kcu.table_name, kcu.column_name
            FROM information_schema.key_column_usage kcu
            JOIN information_schema.table_constraints tc ON kcu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
          )
        """,
        lambda res: f"Found {len(res)} columns ending in '_id' without FK constraints (check manually): {[r[0]+'.'+r[1] for r in res]}" if len(res) > 0 else None,
        severity="WARN"
    )

    # ==========================================
    # 2. Semantic Layer & JSON Structure
    # ==========================================

    # Check 2.1: Invalid Label Structure in posts_hot
    # JSONB checks are powerful in PG
    check(
        "JSON Label Structure",
        """
        SELECT count(*) FROM posts_hot p, jsonb_array_elements(p.content_labels) label
        WHERE NOT (label ? 'category' AND label ? 'sentiment' AND label ? 'confidence')
        """,
        lambda res: f"Found {res[0][0]} label objects missing required keys (category, sentiment, confidence)" if res[0][0] > 0 else None
    )

    # Check 2.2: Entity Structure
    check(
        "JSON Entity Structure",
        """
        SELECT count(*) FROM posts_hot p, jsonb_array_elements(p.entities) ent
        WHERE NOT (ent ? 'name' AND ent ? 'type')
        """,
        lambda res: f"Found {res[0][0]} entity objects missing keys (name, type)" if res[0][0] > 0 else None
    )

    # ==========================================
    # 3. Vector Data Health
    # ==========================================

    # Check 3.1: Embedding Coverage for Active Hot Posts
    check(
        "Embedding Coverage Gap",
        """
        SELECT 
            (SELECT count(*) FROM posts_hot) as total_hot,
            (SELECT count(*) FROM post_embeddings) as total_vectors
        """,
        lambda res: f"Coverage Gap: {res[0][0] - res[0][1]} posts missing embeddings ({res[0][1]}/{res[0][0]})" if res[0][0] > res[0][1] else None,
        severity="WARN" # It's okay if not fully synced immediately, but good to know
    )

    # Check 3.2: Vector Dimension Integrity (Must be 1024)
    check(
        "Vector Dimensions",
        "SELECT count(*) FROM post_embeddings WHERE vector_dims(embedding) != 1024",
        lambda res: f"Found {res[0][0]} vectors with incorrect dimensions (Not 1024)" if res[0][0] > 0 else None
    )

    # ==========================================
    # 4. Business Logic & Data Quality
    # ==========================================

    # Check 4.1: Community Categories JSON
    check(
        "Community Categories Format",
        "SELECT count(*) FROM community_pool WHERE jsonb_typeof(categories) != 'array'",
        lambda res: f"Found {res[0][0]} communities with invalid categories format (not array)" if res[0][0] > 0 else None
    )

    # Check 4.2: SCD2 Strictness (Multiple 'current' versions)
    check(
        "SCD2 Multiple Current Versions",
        "SELECT count(*) FROM (SELECT source_post_id FROM posts_raw WHERE is_current = true GROUP BY source_post_id HAVING count(*) > 1) x",
        lambda res: f"CRITICAL: Found {res[0][0]} posts with multiple active versions!" if res[0][0] > 0 else None
    )

    # Check 4.3: Tier 1 Consistency
    check(
        "Tier 1 Consistency",
        "SELECT count(*) FROM community_pool WHERE is_active=true AND lower(tier) != 'high'",
        lambda res: f"Found {res[0][0]} active communities not labeled 'high'" if res[0][0] > 0 else None
    )
    
    # Check 4.4: Hot Cache Expiry Logic
    check(
        "Hot Cache Stale Data",
        "SELECT count(*) FROM posts_hot WHERE expires_at < NOW()",
        lambda res: f"Found {res[0][0]} expired posts in Hot Cache (Cleanup needed)" if res[0][0] > 0 else None,
        severity="WARN"
    )

    conn.close()

    print("\n" + "="*40)
    print("AUDIT SUMMARY")
    print("="*40)
    
    if not issues_found and not warnings:
        print("🌟 PERFECT SCORE. Database is structurally sound, logically consistent, and ready for scale.")
    
    if warnings:
        print("\n⚠️ WARNINGS (Non-blocking but require attention):")
        for w in warnings:
            print(f"  - {w}")
            
    if issues_found:
        print("\n❌ ERRORS (Must Fix):")
        for i in issues_found:
            print(f"  - {i}")
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    run_comprehensive_audit()