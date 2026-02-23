import sys
import logging
from sqlalchemy import text
from app.db.session import SessionFactory
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DB_GUARD")

MIN_POSTS_THRESHOLD = 1000  # 如果帖子少于 1000，认为库是空的或损坏的

async def check_data_watermark():
    """
    Check if the database has enough data to be considered 'healthy' for analysis.
    """
    async with SessionFactory() as session:
        try:
            # Check connection first
            await session.execute(text("SELECT 1"))
            
            # Check data volume
            result = await session.execute(text("SELECT COUNT(*) FROM posts_raw"))
            count = result.scalar_one()
            
            if count < MIN_POSTS_THRESHOLD:
                logger.error(f"🛑 DATA SAFETY STOP: Database has only {count} posts (Threshold: {MIN_POSTS_THRESHOLD}).")
                logger.error("   This looks like an EMPTY or RESET database.")
                logger.error("   ACTION REQUIRED: Run 'make restore-db' to recover data.")
                return False
            
            logger.info(f"✅ Data Watermark OK: {count} posts found.")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database check failed with error: {e}")
            return False

if __name__ == "__main__":
    # Run async check
    success = asyncio.run(check_data_watermark())
    if not success:
        sys.exit(1)
    sys.exit(0)
