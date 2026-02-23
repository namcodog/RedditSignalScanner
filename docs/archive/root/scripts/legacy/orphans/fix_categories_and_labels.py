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

def fix_db():
    db_url = load_env_config()
    if not db_url:
        print("❌ Error: DATABASE_URL not found")
        return

    engine = create_engine(db_url)
    conn = engine.connect()
    trans = conn.begin()
    
    print("🚑 Starting Surgical Repair...\n")

    try:
        # ==========================================
        # 1. Fix Categories: Object -> Array
        # ==========================================
        print("=== 1. Fixing Categories Format ===")
        
        # Scenario A: Has 'category' key (e.g. {'category': 'Home_Lifestyle'})
        # Action: Extract value, wrap in array
        res_a = conn.execute(text(
            """
            UPDATE community_pool
            SET categories = jsonb_build_array(categories->>'category')
            WHERE jsonb_typeof(categories) = 'object' 
              AND categories ? 'category'
            """
        ))
        print(f"✅ Recovered categories for {res_a.rowcount} communities (extracted from 'category' key)")

        # Scenario B: Junk Object (e.g. {'source': 'csv...'}) 
        # Action: Reset to empty array []
        res_b = conn.execute(text(
            """
            UPDATE community_pool
            SET categories = '[]'::jsonb
            WHERE jsonb_typeof(categories) = 'object'
            """
        ))
        print(f"✅ Reset {res_b.rowcount} communities with junk categories to []")
        
        # Scenario C: Null or other types
        res_c = conn.execute(text(
            """
            UPDATE community_pool
            SET categories = '[]'::jsonb
            WHERE categories IS NULL OR jsonb_typeof(categories) != 'array'
            """
        ))
        print(f"✅ Normalized {res_c.rowcount} other communities to []")

        # ==========================================
        # 2. Fix Content Labels (Missing Sentiment)
        # ==========================================
        print("\n=== 2. Fixing Content Labels (Missing Sentiment) ===")
        
        # We need to iterate and fix because updating specific objects inside a JSONB array 
        # via pure SQL is complex and error-prone in older PG versions.
        # However, we can use a smart replacement logic if we assume the structure.
        # Let's simply UPDATE the whole array by re-constructing it with defaults.
        
        # Complex Query: For each element, if sentiment missing, add it.
        query_fix_labels = """
        UPDATE posts_hot
        SET content_labels = (
            SELECT jsonb_agg(
                CASE 
                    WHEN NOT (elem ? 'sentiment') THEN elem || '{"sentiment": "neutral"}'::jsonb
                    ELSE elem
                END
            )
            FROM jsonb_array_elements(content_labels) elem
        )
        WHERE EXISTS (
            SELECT 1 
            FROM jsonb_array_elements(content_labels) elem 
            WHERE NOT (elem ? 'sentiment')
        );
        """
        res_labels = conn.execute(text(query_fix_labels))
        print(f"✅ Patched labels for {res_labels.rowcount} posts")

        # ==========================================
        # 3. Fix Content Labels (Missing Confidence)
        # ==========================================
        query_fix_conf = """
        UPDATE posts_hot
        SET content_labels = (
            SELECT jsonb_agg(
                CASE 
                    WHEN NOT (elem ? 'confidence') THEN elem || '{"confidence": 0.8}'::jsonb
                    ELSE elem
                END
            )
            FROM jsonb_array_elements(content_labels) elem
        )
        WHERE EXISTS (
            SELECT 1 
            FROM jsonb_array_elements(content_labels) elem 
            WHERE NOT (elem ? 'confidence')
        );
        """
        res_conf = conn.execute(text(query_fix_conf))
        print(f"✅ Patched confidence for {res_conf.rowcount} posts")
        
        trans.commit()
        print("\n✨ Repair Complete! Database Logic Restored.")
        
    except Exception as e:
        trans.rollback()
        print(f"\n❌ CRITICAL ERROR during repair: {e}")
        print("🔄 Rolled back all changes.")

    conn.close()

if __name__ == "__main__":
    fix_db()
