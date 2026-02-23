import asyncio
import os
import sys
import logging
from datetime import datetime, timezone

# Ensure backend is in path
sys.path.insert(0, os.path.join(os.getcwd(), "backend"))

from app.core.config import get_settings
from app.services.reddit_client import RedditAPIClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suspect Communities (Green List - Should have data but showing 0)
TARGETS = [
    "r/amazonwarehouse", 
    "r/bestbuyaliexpress", 
    "r/shopify_users",
    "r/achadinhosdashopeebr",
    "r/aliexpressreviews"
]

async def debug_community(api: RedditAPIClient, subreddit: str):
    logger.info(f"🕵️‍♂️ Probing {subreddit}...")
    
    try:
        # 1. Check Subreddit Info (Is it NSFW? Private?)
        # Note: Our client wraps PRAW, let's use raw access if possible or standard fetch
        
        # 2. Try Fetching /new
        posts, after = await api.fetch_subreddit_posts(
            subreddit.replace("r/", ""), 
            limit=10, 
            sort="new"
        )
        
        if not posts:
            logger.error(f"❌ {subreddit}: API returned 0 posts!")
            return

        logger.info(f"✅ {subreddit}: API returned {len(posts)} posts.")
        for p in posts[:3]:
            logger.info(f"   - [{p.created_utc}] {p.title} (Type: {p.url})")
            
            # Check filters
            if p.title == "[placeholder missing post]":
                logger.warning(f"   ⚠️ Garbage Title Detected")
            
    except Exception as e:
        logger.error(f"💥 {subreddit} Crashed: {e}")

async def main():
    settings = get_settings()
    async with RedditAPIClient(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
    ) as api:
        await api.authenticate()
        
        for target in TARGETS:
            await debug_community(api, target)

if __name__ == "__main__":
    asyncio.run(main())
