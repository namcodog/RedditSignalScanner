import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Ensure we can import from backend
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def load_env_config():
    """Load database URL from .env file and ensure synchronous driver"""
    env_path = os.path.join(os.path.dirname(__file__), '../.env')
    load_dotenv(env_path)
    url = os.getenv('DATABASE_URL')
    if url and '+asyncpg' in url:
        return url.replace('+asyncpg', '+psycopg2')
    return url

def run_health_check():
    db_url = load_env_config()
    if not db_url:
        print("❌ Error: DATABASE_URL not found in .env")
        return

    try:
        engine = create_engine(db_url)
        connection = engine.connect()
        print("✅ Connected to Database successfully.\n")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    checks = [
        {
            "name": "Active Community Count (Target: ~129)",
            "query": "SELECT count(*) FROM community_pool WHERE is_active = true;",
            "expected_min": 120,
            "expected_max": 140
        },
        {
            "name": "Tier 1 Normalization (Target: 0 Non-Tier-1 Active)",
            # Check for active communities that are NOT 'High' or 'Tier 1' (case-insensitive)
            "query": "SELECT count(*) FROM community_pool WHERE is_active = true AND lower(tier) NOT IN ('high', 'tier 1', 'tier1');",
            "expected": 0
        },
        {
            "name": "Prefix Integrity - Community Pool (Target: 0 invalid)",
            "query": "SELECT count(*) FROM community_pool WHERE name NOT LIKE 'r/%';",
            "expected": 0
        },
        {
            "name": "Prefix Integrity - Posts Raw (Target: 0 invalid)",
            "query": "SELECT count(*) FROM posts_raw WHERE subreddit NOT LIKE 'r/%';",
            "expected": 0
        },
         {
            "name": "Prefix Integrity - Community Cache (Target: 0 invalid)",
            "query": "SELECT count(*) FROM community_cache WHERE community_name NOT LIKE 'r/%';",
            "expected": 0
        },
        {
            "name": "SCD2 Integrity (Target: 0 duplicates)",
            # Checks if any post has multiple 'current' versions
            "query": "SELECT count(*) FROM (SELECT source_post_id FROM posts_raw WHERE is_current = true GROUP BY source_post_id HAVING count(*) > 1) as sub;",
            "expected": 0
        },
        {
            "name": "Time Travel Check (Target: 0)",
            # created_at should not be significantly after fetched_at
            "query": "SELECT count(*) FROM posts_raw WHERE created_at > fetched_at + interval '1 hour';",
            "expected": 0
        },
        {
            "name": "Orphaned Comments (Target: 0)",
            # Comments referencing non-existent posts
            "query": "SELECT count(*) FROM comments c LEFT JOIN posts_raw p ON c.post_id = p.id WHERE p.id IS NULL;",
            "expected": 0
        }
    ]

    print("=== 🏥 Database Health Check Report ===\n")
    
    all_passed = True

    for check in checks:
        try:
            result = connection.execute(text(check["query"])).scalar()
            
            status = "✅ PASS"
            if "expected" in check and result != check["expected"]:
                status = f"❌ FAIL (Expected {check['expected']}, Got {result})"
                all_passed = False
            elif "expected_min" in check:
                if not (check["expected_min"] <= result <= check["expected_max"]):
                    status = f"⚠️ WARN (Expected {check['expected_min']}-{check['expected_max']}, Got {result})"
                    # Warning doesn't fail the build, but worth noting
                else:
                     status = f"✅ PASS (Got {result})"
            else:
                status = f"✅ PASS (Got {result})"

            print(f"{check['name']}: {status}")
            
        except Exception as e:
            print(f"❌ Error executing {check['name']}: {e}")
            all_passed = False

    print("\n=== 📊 Storage Baseline ===")
    stats_queries = [
        ("Total Posts (Raw)", "SELECT count(*) FROM posts_raw;"),
        ("Active Posts (Current)", "SELECT count(*) FROM posts_raw WHERE is_current = true;"),
        ("Total Comments", "SELECT count(*) FROM comments;"),
        ("Hot Cache Size", "SELECT count(*) FROM posts_hot;"),
        ("Community Pool Size", "SELECT count(*) FROM community_pool;"),
        ("Community Cache Size", "SELECT count(*) FROM community_cache;")
    ]

    for label, query in stats_queries:
        try:
            res = connection.execute(text(query)).scalar()
            print(f"{label}: {res:,}")
        except Exception as e:
            print(f"{label}: Error {e}")

    connection.close()
    
    if not all_passed:
        print("\n❌ Health Check Failed. Please investigate failures before backfilling.")
        sys.exit(1)
    else:
        print("\n✅ System Healthy. Ready for Backfill.")
        sys.exit(0)

if __name__ == "__main__":
    run_health_check()
