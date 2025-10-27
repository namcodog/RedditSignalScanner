"""Celery task for syncing community member counts from Reddit API.

This task periodically fetches member counts for all active communities
and updates the community_cache table. This replaces the hardcoded
DEFAULT_COMMUNITY_MEMBERS dictionary.

Related to: P1-5 (硬编码的社区成员数)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.services.reddit_client import RedditAPIClient, RedditAPIError

logger = logging.getLogger(__name__)


async def _sync_community_members_impl() -> dict[str, Any]:
    """Implementation of community member count sync.
    
    Fetches member counts from Reddit API for all active communities
    and updates the community_cache table.
    
    Returns:
        dict: Sync statistics including success/failure counts
    """
    settings = get_settings()
    
    # Initialize Reddit client
    reddit_client = RedditAPIClient(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
    )
    
    stats = {
        "total_communities": 0,
        "successful_updates": 0,
        "failed_updates": 0,
        "skipped_communities": 0,
        "errors": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    
    try:
        async with reddit_client:
            async with SessionFactory() as db:
                # Get all active communities
                result = await db.execute(
                    select(CommunityCache.community_name)
                    .where(CommunityCache.is_active == True)
                    .order_by(CommunityCache.community_name)
                )
                communities = result.scalars().all()
                stats["total_communities"] = len(communities)
                
                logger.info(f"Starting member count sync for {len(communities)} communities")
                
                # Process communities in batches to avoid overwhelming the API
                batch_size = 50
                for i in range(0, len(communities), batch_size):
                    batch = communities[i:i + batch_size]
                    
                    for community_name in batch:
                        try:
                            # Fetch subreddit info from Reddit API
                            # Note: We use the about endpoint to get subscriber count
                            member_count = await _fetch_member_count(
                                reddit_client, 
                                community_name
                            )
                            
                            if member_count is not None:
                                # Update community_cache with member count
                                await db.execute(
                                    update(CommunityCache)
                                    .where(CommunityCache.community_name == community_name)
                                    .values(
                                        member_count=member_count,
                                        updated_at=datetime.now(timezone.utc),
                                    )
                                )
                                stats["successful_updates"] += 1
                                logger.debug(
                                    f"Updated {community_name}: {member_count:,} members"
                                )
                            else:
                                stats["skipped_communities"] += 1
                                logger.warning(
                                    f"Skipped {community_name}: unable to fetch member count"
                                )
                                
                        except RedditAPIError as e:
                            stats["failed_updates"] += 1
                            error_msg = f"{community_name}: {str(e)}"
                            stats["errors"].append(error_msg)
                            logger.error(f"Reddit API error for {community_name}: {e}")
                            
                        except Exception as e:
                            stats["failed_updates"] += 1
                            error_msg = f"{community_name}: {str(e)}"
                            stats["errors"].append(error_msg)
                            logger.exception(f"Unexpected error for {community_name}: {e}")
                    
                    # Commit batch
                    await db.commit()
                    logger.info(
                        f"Processed batch {i//batch_size + 1}: "
                        f"{stats['successful_updates']}/{stats['total_communities']} updated"
                    )
                    
                    # Small delay between batches to respect rate limits
                    if i + batch_size < len(communities):
                        await asyncio.sleep(2)
                
    except Exception as e:
        logger.exception(f"Fatal error during member count sync: {e}")
        stats["errors"].append(f"Fatal error: {str(e)}")
        raise
    
    finally:
        stats["completed_at"] = datetime.now(timezone.utc).isoformat()
        
    logger.info(
        f"Member count sync completed: "
        f"{stats['successful_updates']} updated, "
        f"{stats['failed_updates']} failed, "
        f"{stats['skipped_communities']} skipped"
    )
    
    return stats


async def _fetch_member_count(
    reddit_client: RedditAPIClient, 
    community_name: str
) -> int | None:
    """Fetch member count for a single community from Reddit API.
    
    Args:
        reddit_client: Authenticated Reddit API client
        community_name: Community name (e.g., 'startups')
        
    Returns:
        Member count or None if unable to fetch
    """
    try:
        # Ensure authentication
        await reddit_client.authenticate()
        
        # Fetch subreddit about info
        # Reddit API endpoint: /r/{subreddit}/about
        url = f"https://oauth.reddit.com/r/{community_name}/about"
        headers = {
            "Authorization": f"Bearer {reddit_client.access_token}",
            "User-Agent": reddit_client.user_agent,
        }
        
        # Use the client's internal request method
        payload = await reddit_client._request_json("GET", url, headers=headers)
        
        # Extract subscriber count from response
        # Response structure: {"data": {"subscribers": 123456, ...}}
        if isinstance(payload, dict) and "data" in payload:
            data = payload["data"]
            if isinstance(data, dict) and "subscribers" in data:
                return int(data["subscribers"])
        
        logger.warning(f"Unexpected response structure for {community_name}: {payload}")
        return None
        
    except RedditAPIError as e:
        logger.error(f"Reddit API error fetching member count for {community_name}: {e}")
        raise
        
    except Exception as e:
        logger.exception(f"Error fetching member count for {community_name}: {e}")
        return None


@celery_app.task(name="tasks.community.sync_member_counts", bind=True, max_retries=3)  # type: ignore[misc]
def sync_community_member_counts(self: Any) -> dict[str, Any]:
    """Celery task to sync community member counts from Reddit API.
    
    This task runs periodically (configured in celery_app.py beat_schedule)
    to keep member counts up-to-date in the community_cache table.
    
    Returns:
        dict: Sync statistics
    """
    try:
        return asyncio.run(_sync_community_members_impl())
    except RedditAPIError as exc:
        logger.error(f"Reddit API error during member count sync: {exc}")
        raise self.retry(exc=exc, countdown=300)  # Retry after 5 minutes
    except Exception as exc:
        logger.exception(f"Unexpected error during member count sync: {exc}")
        raise self.retry(exc=exc, countdown=600)  # Retry after 10 minutes


__all__ = ["sync_community_member_counts"]

