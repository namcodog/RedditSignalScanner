import os
import sys
import logging
from sqlalchemy import create_engine, text

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_URL = f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'reddit_signal_scanner')}"

def backfill_authors_orphan_loop():
    engine = create_engine(DB_URL)
    conn = engine.connect()
    
    logger.info("Starting Orphan-Based Author Backfill...")
    
    # 1. Ensure table
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.authors (
            author_id VARCHAR(100) PRIMARY KEY,
            author_name VARCHAR(100),
            created_utc TIMESTAMPTZ,
            is_bot BOOLEAN DEFAULT false NOT NULL,
            first_seen_at_global TIMESTAMPTZ DEFAULT NOW() NOT NULL
        );
    """))
    conn.commit()

    total_inserted = 0

    while True:
        # Find orphans
        # Using NOT EXISTS is often faster than NOT IN for large tables
        fetch_query = text("""
            SELECT DISTINCT author_id, author_name, MIN(created_at) as first_seen
            FROM public.posts_raw p
            WHERE author_id IS NOT NULL 
              AND author_id != ''
              AND NOT EXISTS (SELECT 1 FROM public.authors a WHERE a.author_id = p.author_id)
            GROUP BY author_id, author_name
            LIMIT 5000
        """)
        
        try:
            # Select orphans first
            result = conn.execute(fetch_query).fetchall()
            if not result:
                logger.info("No more orphans found. Backfill complete.")
                break
            
            logger.info(f"Found {len(result)} orphans. Inserting...")
            
            # Batch insert
            # We use direct INSERT VALUES to avoid complex INSERT SELECT locking issues
            insert_values = [
                {"aid": row.author_id, "aname": row.author_name, "atime": row.first_seen}
                for row in result
            ]
            
            conn.execute(text("""
                INSERT INTO public.authors (author_id, author_name, first_seen_at_global)
                VALUES (:aid, :aname, :atime)
                ON CONFLICT (author_id) DO NOTHING
            """), insert_values)
            
            conn.commit()
            total_inserted += len(result)
            logger.info(f"  -> Inserted batch. Total so far: {total_inserted}")
            
        except Exception as e:
            logger.error(f"Chunk failed: {e}")
            # If a read query fails (e.g. timeout), we might be stuck.
            # But SELECT ... LIMIT 5000 usually runs fast.
            break
        

    # 3. Add FK
    logger.info("Adding Foreign Key constraint...")
    try:
        # Increase timeout for index creation/validation
        conn.execute(text("SET LOCAL statement_timeout = '300s'"))
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'fk_posts_raw_author'
                ) THEN
                    ALTER TABLE public.posts_raw 
                        ADD CONSTRAINT fk_posts_raw_author 
                        FOREIGN KEY (author_id) 
                        REFERENCES public.authors(author_id) 
                        ON DELETE SET NULL;
                END IF;
            END $$;
        """))
        conn.commit()
        logger.info("Foreign Key added successfully.")
    except Exception as e:
        logger.error(f"Failed to add FK: {e}")

    conn.close()

if __name__ == "__main__":
    backfill_authors_orphan_loop()
