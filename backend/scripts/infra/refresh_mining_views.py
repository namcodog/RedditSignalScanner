import asyncio
import logging
import sys
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, OperationalError
from app.db.session import SessionFactory

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VIEW_REFRESHER")

VIEWS_TO_REFRESH = [
    "mv_analysis_labels",
    "mv_analysis_entities"
]

async def refresh_views():
    """
    Refreshes the materialized views required for the Analysis Engine.
    Follows SOP v2 Section 2: Data Hygiene.
    """
    logger.info("🔄 Starting Materialized View Refresh Cycle...")
    
    async with SessionFactory() as session:
        for view in VIEWS_TO_REFRESH:
            try:
                logger.info(f"   Target: {view} (Mode: CONCURRENTLY)")
                # 尝试按照 SOP 要求使用 CONCURRENTLY
                await session.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}"))
                logger.info(f"   ✅ {view} refreshed successfully.")
                
            except Exception as e:
                # 无论什么错误（通常是缺少索引），都尝试降级到普通模式
                await session.rollback()  # 必须先回滚失败的事务，才能继续执行
                logger.warning(f"   ⚠️ Concurrent refresh failed for {view} (Reason: {str(e).splitlines()[0]}).")
                logger.info(f"   🔄 Falling back to Exclusive Mode (Locks view)...")
                
                try:
                    await session.execute(text(f"REFRESH MATERIALIZED VIEW {view}"))
                    logger.info(f"   ✅ {view} refreshed (Exclusive Mode).")
                except Exception as e2:
                    logger.error(f"   ❌ Failed to refresh {view} even in Exclusive Mode: {e2}")
                    return False
                
    logger.info("✨ All Mining Views are synchronized with Raw Data.")
    return True

if __name__ == "__main__":
    success = asyncio.run(refresh_views())
    if not success:
        sys.exit(1)
    sys.exit(0)
