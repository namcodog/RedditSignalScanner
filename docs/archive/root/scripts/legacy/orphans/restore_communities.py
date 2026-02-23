import os
import subprocess
import sys
from dotenv import load_dotenv

def restore_communities():
    # Load environment variables
    env_path = os.path.join(os.path.dirname(__file__), '../.env')
    load_dotenv(env_path)
    
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ Error: DATABASE_URL not found")
        sys.exit(1)

    # Handle SQLAlchemy specific drivers in URL
    # libpq (pg_restore) only understands 'postgresql://' or 'postgres://'
    if '+asyncpg' in db_url:
        db_url = db_url.replace('+asyncpg', '')
    if '+psycopg2' in db_url:
        db_url = db_url.replace('+psycopg2', '')
    
    backup_file = "backups/prod_backup_post_purge_clean_20251202.dump"
    
    if not os.path.exists(backup_file):
        print(f"❌ Error: Backup file {backup_file} not found")
        sys.exit(1)

    print(f"♻️ Restoring 'community_pool' and 'community_cache' from {backup_file}...")
    
    # Construct pg_restore command
    # -d: database connection string
    # -t: restore specific table
    # -c: clean (drop) database objects before recreating
    # -v: verbose
    cmd = [
        "pg_restore",
        "-d", db_url,
        "-t", "community_pool",
        "-t", "community_cache",
        "--clean",
        "--verbose",
        backup_file
    ]

    try:
        # Run pg_restore. Note: pg_restore might emit warnings to stderr, which is normal.
        process = subprocess.run(cmd, check=True, text=True, capture_output=True)
        print("✅ Restore completed successfully!")
        print(process.stdout)
        print(process.stderr) # Print stderr as it contains the verbose logs
    except subprocess.CalledProcessError as e:
        print("❌ Restore Failed!")
        print(e.stderr)
        sys.exit(1)

if __name__ == "__main__":
    restore_communities()
