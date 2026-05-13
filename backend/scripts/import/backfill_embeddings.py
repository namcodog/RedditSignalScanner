import asyncio
import logging
import sys
import os
from pathlib import Path

# Ensure backend is in pythonpath so imports work
# Add Root (for backend.app...)
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
# Add Backend (for app...)
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from backend.app.db.session import SessionFactory
from backend.app.services.semantic.embedding_service import embedding_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
BATCH_SIZE = 32  # Balanced for speed/stability
MODEL_VERSION = "BAAI/bge-m3"

async def backfill_embeddings():
    """
    Backfill embeddings for posts that don't have them.
    """
    logger.info(f"🚀 Starting embedding backfill (Model: {MODEL_VERSION}, Batch: {BATCH_SIZE})")
    
    total_processed = 0
    
    while True:
        async with SessionFactory() as session:
            # 1. Fetch posts without embeddings
            # Using LEFT JOIN to find missing entries
            stmt = text("""
                SELECT p.id, p.title, p.body 
                FROM posts_raw p
                LEFT JOIN post_embeddings pe ON pe.post_id = p.id
                WHERE p.is_current = true 
                  AND pe.post_id IS NULL
                LIMIT :limit
            """)
            
            result = await session.execute(stmt, {"limit": BATCH_SIZE})
            rows = result.fetchall()
            
            if not rows:
                logger.info("✅ All caught up! No more posts to embed.")
                break
            
            batch_count = len(rows)
            logger.info(f"Processing batch of {batch_count} posts...")
            
            # 2. Prepare text content
            ids = []
            texts = []
            for row in rows:
                # Combine title + body. 
                # Handle None body.
                # Truncate to prevent memory OOM on massive posts
                content = f"{row.title}\n{row.body or ''}".strip()[:2000]
                ids.append(row.id)
                texts.append(content)
            
        # Session closed here to release DB connection while we do heavy ML inference
        # This prevents "ConnectionDoesNotExistError" and long transactions
        
        # 3. Generate Embeddings (CPU/GPU bound, no DB needed)
        try:
            # This handles model loading internally
            embeddings = embedding_service.encode(texts, batch_size=batch_count)
        except Exception as e:
            logger.error(f"❌ Failed to generate embeddings for batch: {e}")
            break

        # 4. Insert into DB (New Session)
        async with SessionFactory() as session:
            insert_data = []
            for pid, vec in zip(ids, embeddings):
                insert_data.append({
                    "post_id": pid,
                    "model_version": MODEL_VERSION,
                    "embedding": str(vec)  # Explicitly convert list to string for pgvector
                })
            
            # Using raw SQL for bulk insert efficiency
            insert_stmt = text("""
                INSERT INTO post_embeddings (post_id, model_version, embedding)
                VALUES (:post_id, :model_version, :embedding)
            """)
            
            try:
                await session.execute(insert_stmt, insert_data)
                await session.commit()
                total_processed += batch_count
                logger.info(f"   💾 Saved {batch_count} embeddings. Total processed: {total_processed}")
            except Exception as e:
                logger.error(f"❌ Database insert failed: {e}")
                await session.rollback()
                break
                
    logger.info("🏁 Backfill process finished.")

if __name__ == "__main__":
    try:
        asyncio.run(backfill_embeddings())
    except KeyboardInterrupt:
        logger.info("🛑 Process interrupted by user.")
    except Exception as e:
        logger.exception(f"💥 Fatal error: {e}")
