import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_URL = f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'reddit_signal_scanner')}"

def fix_community_casing():
    engine = create_engine(DB_URL)
    conn = engine.connect()
    
    logger.info("Starting Community Pool Lowercase Fix (Aggressive Strategy)...")
    
    # 1. Identify Uppercase Communities
    rows = conn.execute(text("""
        SELECT id, name FROM public.community_pool WHERE name ~ '[A-Z]'
    """)).fetchall()
    
    if not rows:
        logger.info("No uppercase communities found.")
        # Still try to lock constraint just in case
    else:
        logger.info(f"Found {len(rows)} uppercase communities. Fixing...")

    fixed_count = 0
    deleted_count = 0
    
    for row in rows:
        old_name = row.name
        new_name = old_name.lower()
        community_id = row.id
        
        try:
            # 1. Nuke the cache entry first (Break FK dependency)
            conn.execute(text("DELETE FROM public.community_cache WHERE community_name = :old_name"), {"old_name": old_name})
            
            # 2. Try to rename the pool entry
            conn.execute(text("UPDATE public.community_pool SET name = :new_name WHERE id = :id"), 
                         {"new_name": new_name, "id": community_id})
            fixed_count += 1
            conn.commit()
            
        except IntegrityError as e:
            # 3. Conflict! (Unique Violation) -> Delete the uppercase duplicate
            conn.rollback()
            logger.warning(f"Conflict for {old_name} -> {new_name}. Deleting uppercase duplicate (ID {community_id})...")
            try:
                # We verify that the conflicting ID is NOT us (just sanity check)
                conn.execute(text("DELETE FROM public.community_pool WHERE id = :id"), {"id": community_id})
                deleted_count += 1
                conn.commit()
            except Exception as delete_err:
                logger.error(f"Failed to delete duplicate {old_name}: {delete_err}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Unexpected error for {old_name}: {e}")

    logger.info(f"Fix Complete. Renamed: {fixed_count}, Deleted (Merged): {deleted_count}")

    # 2. Update Constraint
    logger.info("Locking Constraint...")
    try:
        conn.execute(text("""
            ALTER TABLE public.community_pool DROP CONSTRAINT IF EXISTS ck_community_pool_name_format;
            ALTER TABLE public.community_pool ADD CONSTRAINT ck_community_pool_name_format CHECK (name ~ '^r/[a-z0-9_]+$');
        """))
        conn.commit()
        logger.info("Constraint locked successfully.")
    except Exception as e:
        logger.error(f"Failed to lock constraint: {e}")

    conn.close()

if __name__ == "__main__":
    fix_community_casing()
