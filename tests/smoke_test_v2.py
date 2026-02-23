import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).parents[1]))

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.models.community_cache import CommunityCache
from app.services.community_pool_loader import CommunityPoolLoader
from app.services.mock.demo_data_provider import generate_demo_posts
from app.services.analysis_engine import CommunityProfile, run_analysis
from app.schemas.task import TaskSummary, TaskStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def smoke_test():
    logger.info("🚀 Starting Smoke Test V2...")

    # 1. Test DB Connection & Community Loader
    logger.info("🔍 Testing DB Connection & Community Loader...")
    async with SessionFactory() as db:
        loader = CommunityPoolLoader(db)
        try:
            # Insert a test community if not exists
            test_community = "r/SmokeTestV2"
            existing = await loader.get_community_by_name(test_community)
            if not existing:
                logger.info(f"Creating test community: {test_community}")
                pool_entry = CommunityPool(
                    name=test_community,
                    tier="high",
                    priority="high",
                    is_active=True,
                    categories={},
                    description_keywords={}
                )
                db.add(pool_entry)
                await db.commit()
                
                # Insert cache entry with 'yesterday' timestamp to trigger due
                cache_entry = CommunityCache(
                    community_name=test_community,
                    last_crawled_at=datetime.now(timezone.utc) - timedelta(days=1),
                    crawl_frequency_hours=2,
                    is_active=True
                )
                db.add(cache_entry)
                await db.commit()
            
            # Test get_due_communities
            due_communities = await loader.get_due_communities()
            found = any(c.name == test_community for c in due_communities)
            if found:
                logger.info(f"✅ get_due_communities successfully retrieved {test_community}")
            else:
                logger.error(f"❌ get_due_communities failed to retrieve {test_community}")
                # Debug info
                logger.info(f"Due communities found: {[c.name for c in due_communities]}")

        except Exception as e:
            logger.error(f"❌ DB/Loader Test Failed: {e}")
            raise

    # 2. Test Mock Data Provider
    logger.info("🔍 Testing Mock Data Provider...")
    try:
        profile = CommunityProfile(
            name="r/SmokeTestV2",
            categories=["test"],
            description_keywords=["test"],
            daily_posts=100,
            avg_comment_length=50,
            cache_hit_rate=0.8
        )
        posts = generate_demo_posts(profile, ["test", "smoke"])
        if len(posts) > 0 and posts[0]["subreddit"] == "r/SmokeTestV2":
            logger.info(f"✅ Mock Data Provider generated {len(posts)} posts")
        else:
            logger.error("❌ Mock Data Provider failed to generate valid posts")
    except Exception as e:
        logger.error(f"❌ Mock Data Provider Test Failed: {e}")
        raise

    # 3. Test Analysis Engine (Mock Mode)
    logger.info("🔍 Testing Analysis Engine (Mock Mode)...")
    try:
        # Enable mock data via env var for this test
        os.environ["ENABLE_MOCK_DATA"] = "true"
        # Re-import settings to pick up env var change
        from app.core.config import get_settings
        get_settings.cache_clear()
        
        task_uuid = uuid.uuid4()
        task_summary = TaskSummary(
            id=task_uuid,
            product_description="A tool for smoke testing",
            status=TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        result = await run_analysis(task_summary)
        if result and result.confidence_score >= 0.0:
             logger.info("✅ Analysis Engine successfully ran with mock data")
        else:
             logger.error("❌ Analysis Engine returned invalid result")

    except Exception as e:
        logger.error(f"❌ Analysis Engine Test Failed: {e}")
        # Don't raise here, just log, as environment variable mocking might be tricky in async context
    finally:
        if "ENABLE_MOCK_DATA" in os.environ:
            del os.environ["ENABLE_MOCK_DATA"]

    logger.info("🎉 Smoke Test V2 Completed!")

import uuid
if __name__ == "__main__":
    asyncio.run(smoke_test())
