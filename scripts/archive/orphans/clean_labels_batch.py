import os
import logging
import time
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

DB_URL = f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'reddit_signal_scanner')}"

def clean_labels_optimized():
    engine = create_engine(DB_URL)
    conn = engine.connect()
    
    logger.info("Starting Optimized Batch Label Cleanup...")
    
    # 1. Clean Posts Labels (Already mostly done, but check again)
    # We iterate until no orphans found
    clean_entity(conn, 'post', 'posts_raw')

    # 2. Clean Comments Labels
    clean_entity(conn, 'comment', 'comments')

    logger.info("Cleanup Complete.")
    conn.close()

def clean_entity(conn, c_type, table_name):
    total_deleted = 0
    batch_size = 2000 # Smaller batch to be safe
    
    logger.info(f"Cleaning orphans for {c_type} -> {table_name}...")
    
    while True:
        # Step 1: Select IDs to delete (Read is faster than Write)
        # We use a limit to avoid scanning too much
        select_sql = text(f"""
            SELECT l.id 
            FROM public.content_labels l
            WHERE l.content_type = :ctype
              AND NOT EXISTS (SELECT 1 FROM public.{table_name} t WHERE t.id = l.content_id)
            LIMIT :limit
        """)
        
        try:
            result = conn.execute(select_sql, {"ctype": c_type, "limit": batch_size}).fetchall()
            if not result:
                logger.info(f"No more orphans found for {c_type}.")
                break
            
            ids_to_delete = [row[0] for row in result]
            
            # Step 2: Delete by ID (Very fast)
            delete_sql = text("DELETE FROM public.content_labels WHERE id = ANY(:ids)")
            conn.execute(delete_sql, {"ids": ids_to_delete})
            conn.commit()
            
            count = len(ids_to_delete)
            total_deleted += count
            logger.info(f"Deleted {count} {c_type} labels. Total: {total_deleted}")
            
            time.sleep(0.05) # Brief pause
            
        except Exception as e:
            logger.error(f"Error cleaning {c_type}: {e}")
            conn.rollback()
            # Try to continue or break? Let's break to avoid infinite loop on error
            break

if __name__ == "__main__":
    clean_labels_optimized()