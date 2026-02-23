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

def audit_engine():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🟡 Auditing The Engine (Tasks & Ops)...")
    
    # 1. Tasks Status
    print("=== 1. Task Queue Status ===")
    task_stats = conn.execute(text("""
        SELECT status, count(*) 
        FROM tasks 
        GROUP BY status
    """)).fetchall()
    
    if not task_stats:
        print("  (No tasks recorded yet)")
    for status, count in task_stats:
        print(f"  {status}: {count}")
        
    # 2. Crawl Metrics (Health Heartbeat)
    print("\n=== 2. Crawl Metrics (Heartbeat) ===")
    last_metric = conn.execute(text("""
        SELECT created_at, total_communities, successful_crawls, failed_crawls 
        FROM crawl_metrics 
        ORDER BY created_at DESC 
        LIMIT 1
    """ )).fetchone()
    
    if last_metric:
        print(f"  Last Heartbeat: {last_metric[0]}")
        print(f"  Stats: {last_metric[1]} comms | {last_metric[2]} success | {last_metric[3]} failed")
    else:
        print("  ⚠️ No crawl metrics found. (System hasn't run recently?)")

    # 3. Discovery Queue
    print("\n=== 3. Discovery Queue ===")
    pending_discovery = conn.execute(text("SELECT count(*) FROM discovered_communities WHERE status = 'pending'")).scalar()
    print(f"  Pending Review: {pending_discovery}")
    
    # 4. Maintenance Log
    print("\n=== 4. Maintenance Log ===")
    last_maint = conn.execute(text("""
        SELECT started_at, task_name, affected_rows 
        FROM maintenance_audit 
        ORDER BY started_at DESC 
        LIMIT 3
    """ )).fetchall()
    
    if last_maint:
        for row in last_maint:
            print(f"  {row[0]}: {row[1]} (Rows: {row[2]})")
    else:
        print("  (No maintenance logs)")

    conn.close()

if __name__ == "__main__":
    audit_engine()
