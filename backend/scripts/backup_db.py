import os
import sys
import subprocess
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def load_env_config():
    env_path = os.path.join(os.path.dirname(__file__), '../.env')
    load_dotenv(env_path)
    url = os.getenv('DATABASE_URL')
    if url and '+asyncpg' in url:
        return url.replace('+asyncpg', '+psycopg2')
    return url

def backup_db():
    db_url = load_env_config()
    if not db_url: 
        print("❌ No DB URL found")
        return

    # Clean URL for pg_dump (remove +psycopg2 etc)
    clean_url = db_url.replace('+psycopg2', '').replace('+asyncpg', '')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"prod_backup_post_pool_rebuild_{timestamp}.dump"
    backup_dir = os.path.join(os.path.dirname(__file__), '../../backups')
    os.makedirs(backup_dir, exist_ok=True)
    filepath = os.path.join(backup_dir, filename)
    
    print(f"💾 Starting Database Backup to {filename}...\n")
    
    cmd = [
        "pg_dump",
        "--format=custom",
        "--no-owner",  # Better for portability
        "--no-acl",    # Better for portability
        "--verbose",
        "--file", filepath,
        clean_url
    ]
    
    try:
        # Run pg_dump
        # Capture output to avoid clutter, print only on error or success summary
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        
        # Check file size
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        print(f"✅ Backup Successful!")
        print(f"   File: {filepath}")
        print(f"   Size: {size_mb:.2f} MB")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Backup Failed!")
        print(e.stderr)

if __name__ == "__main__":
    backup_db()
