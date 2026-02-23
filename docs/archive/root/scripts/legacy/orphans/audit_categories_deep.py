import os
import sys
import json
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

def audit_categories():
    db_url = load_env_config()
    if not db_url: return
    engine = create_engine(db_url)
    conn = engine.connect()
    
    print("🧭 Auditing the 7 Business Categories...\n")

    # 1. Define the Target 7
    targets = [
        "Home_Lifestyle",
        "Tools_EDC",
        "Frugal_Living",
        "Food_Coffee_Lifestyle",
        "Minimal_Outdoor",
        "Family_Parenting",
        "ecommerce" # Assuming 'eop ecommerce' simplifies to this or check fuzzy
    ]
    
    print(f"Target Categories: {targets}\n")

    # 2. Check Coverage in 'categories' array
    print("=== Coverage Analysis (categories field) ===")
    for tag in targets:
        # Check if tag exists in the JSON array
        count = conn.execute(text(
            "SELECT count(*) FROM community_pool WHERE is_active=true AND categories ? :tag"
        ), {"tag": tag}).scalar()
        print(f"  [{tag}]: {count} communities")

    # 3. Check for 'description' and 'reason'
    print("\n=== Description & Reason Hunt ===")
    # Check inside 'description_keywords' (often used for metadata)
    sample_meta = conn.execute(text(
        """
        SELECT name, description_keywords 
        FROM community_pool 
        WHERE is_active=true 
        AND jsonb_typeof(description_keywords) = 'object'
        LIMIT 3
        """
    )).fetchall()
    
    print("Sample 'description_keywords' content:")
    for row in sample_meta:
        print(f"  r/{row[0]}: {row[1]}")

    # Check if 'reason' exists inside the old 'categories' objects (for the inactive ones or recently fixed)
    # We already fixed active ones to arrays, so 'reason' might have been wiped from 'categories' 
    # if it was stored there!
    # Let's check the *Backup* or inactive ones to see where 'reason' used to live.
    print("\nChecking Inactive (Zombie) communities for 'reason' field structure:")
    zombie_sample = conn.execute(text(
        """
        SELECT categories 
        FROM community_pool 
        WHERE is_active=false 
        AND jsonb_typeof(categories) = 'object' 
        AND categories ? 'reason'
        LIMIT 3
        """
    )).fetchall()
    
    if zombie_sample:
        for row in zombie_sample:
            print(f"  Found trace of 'reason': {row[0]}")
    else:
        print("  No trace of 'reason' key found in inactive communities either.")

    conn.close()

if __name__ == "__main__":
    audit_categories()
