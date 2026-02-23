"""Community Evaluator Service - Phase 6: The Gatekeeper

Evaluates discovered communities to determine if they should be
promoted to the active community_pool.

Core Logic:
1. Fetch sample posts from a pending community (Top 50)
2. Score each post using SmartTagger.evaluate_text_content()
3. Calculate Value Density = (High-Value Posts) / Total
4. Approve (>= 30% density) or Reject (< 30%)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discovered_community import DiscoveredCommunity
from app.models.community_pool import CommunityPool
from app.services.semantic.smart_tagger import SemanticTagger, NeedScore
from app.services.reddit_client import RedditAPIClient, RedditPost
from app.utils.subreddit import normalize_subreddit_name

logger = logging.getLogger(__name__)

# Threshold for community approval (30% high-value posts)
VALUE_DENSITY_THRESHOLD = 0.30

# Cooldown period in days for rejected communities
COOLDOWN_DAYS = 90

# Max consecutive rejections before permanent blacklist
MAX_REJECTIONS = 3

# Categories considered "high-value" for density calculation
HIGH_VALUE_CATEGORIES = {"Survival", "Efficiency", "Growth"}


class CommunityEvaluator:
    """Evaluates discovered communities for value and decides approval/rejection."""

    def __init__(
        self,
        db: AsyncSession,
        reddit_client: RedditAPIClient,
        *,
        sample_size: int = 50,
    ) -> None:
        """Initialize the evaluator.
        
        Args:
            db: Async database session
            reddit_client: Reddit API client for fetching sample posts
            sample_size: Number of posts to sample for evaluation
        """
        self.db = db
        self.reddit_client = reddit_client
        self.sample_size = sample_size
        self._tagger: Optional[SemanticTagger] = None

    @property
    def tagger(self) -> SemanticTagger:
        """Lazy-load the SemanticTagger."""
        if self._tagger is None:
            self._tagger = SemanticTagger()
        return self._tagger

    async def evaluate(self, community_name: str) -> dict:
        """Evaluate a single community and decide its fate.
        
        Args:
            community_name: Name of the community to evaluate (e.g., r/shopify)
            
        Returns:
            dict with evaluation results:
            {
                "community": str,
                "status": "approved" | "rejected" | "blacklisted" | "error",
                "value_density": float,
                "sample_size": int,
                "high_value_count": int,
                "breakdown": {category: count},
                "message": str
            }
        """
        # Step 1: Find the pending community
        stmt = select(DiscoveredCommunity).where(
            DiscoveredCommunity.name == community_name,
            DiscoveredCommunity.status == "pending",
        )
        result = await self.db.execute(stmt)
        community = result.scalar_one_or_none()

        if not community:
            return {
                "community": community_name,
                "status": "error",
                "message": f"Community '{community_name}' not found or not pending",
            }

        # Hard gate: if the community is already blacklisted in community_pool,
        # it must never be auto-approved/activated again.
        pool_row = await self.db.execute(
            select(CommunityPool.is_blacklisted).where(CommunityPool.name == community.name)
        )
        if pool_row.scalar_one_or_none() is True:
            now = datetime.now(timezone.utc)
            community.status = "blacklisted"
            community.admin_reviewed_at = now
            community.admin_notes = (
                (community.admin_notes or "").strip() + "\nblocked: community_pool is_blacklisted=true"
            ).strip()
            base_metrics = dict(community.metrics or {})
            base_metrics["evaluation"] = {
                "blocked_by_pool_blacklist": True,
                "evaluated_at": now.isoformat(),
            }
            community.metrics = base_metrics
            await self.db.commit()
            logger.warning("🚫 Blocked evaluation: %s is blacklisted in community_pool", community.name)
            return {
                "community": community.name,
                "status": "blacklisted",
                "message": "blocked: community_pool is_blacklisted=true",
            }

        # Check cooldown
        if community.cooldown_until and community.cooldown_until > datetime.now(timezone.utc):
            return {
                "community": community_name,
                "status": "error",
                "message": f"Community in cooldown until {community.cooldown_until}",
            }

        # 第4：验毒回填没完成，不允许直接评估（避免“先评估后补数”的口径回退）
        metrics: dict = dict(community.metrics or {})
        vetting = metrics.get("vetting") or {}
        if (vetting.get("status") != "completed") and (
            os.getenv("DISCOVERY_REQUIRE_VETTING", "1") == "1"
        ):
            return {
                "community": community.name,
                "status": "skipped",
                "message": "candidate vetting not completed",
            }

        try:
            # Step 2: Prefer DB samples (posts_raw) after vetting; fallback to API only if needed.
            posts = await self._fetch_sample_posts_from_db(community)
            if len(posts) < max(5, self.sample_size // 3):
                posts = await self._fetch_sample_posts(community_name)
            
            if not posts:
                return await self._reject_community(
                    community, 
                    value_density=0.0, 
                    breakdown={},
                    reason="No posts found"
                )

            # Step 3: Evaluate each post
            breakdown = {cat: 0 for cat in HIGH_VALUE_CATEGORIES}
            high_value_count = 0

            for post in posts:
                text_content = f"{post.title}\n{post.selftext or ''}"
                score = self.tagger.evaluate_text_content(text_content)
                primary = score.primary()
                
                if primary in HIGH_VALUE_CATEGORIES:
                    high_value_count += 1
                    breakdown[primary] = breakdown.get(primary, 0) + 1

            # Step 4: Calculate value density
            value_density = high_value_count / len(posts) if posts else 0.0

            # Step 5: Make decision
            if value_density >= VALUE_DENSITY_THRESHOLD:
                return await self._approve_community(
                    community, value_density, breakdown, len(posts), high_value_count
                )
            else:
                return await self._reject_community(
                    community, value_density, breakdown, 
                    reason=f"Value density {value_density:.1%} below threshold {VALUE_DENSITY_THRESHOLD:.0%}"
                )

        except Exception as e:
            logger.error(f"Error evaluating {community_name}: {e}")
            return {
                "community": community_name,
                "status": "error",
                "message": str(e),
            }

    async def _fetch_sample_posts(self, community_name: str) -> List[RedditPost]:
        """Fetch sample posts from a community (mix of Hot and New)."""
        normalized = normalize_subreddit_name(community_name)
        subreddit = normalized[2:] if normalized.startswith("r/") else normalized
        
        posts: List[RedditPost] = []
        half = self.sample_size // 2
        
        try:
            # Get hot posts
            hot_posts, _after = await self.reddit_client.fetch_subreddit_posts(
                subreddit=subreddit, sort="hot", limit=half
            )
            posts.extend(hot_posts)
        except Exception as e:
            logger.warning(f"Failed to fetch hot posts from {subreddit}: {e}")
        
        try:
            # Get new posts
            new_posts, _after = await self.reddit_client.fetch_subreddit_posts(
                subreddit=subreddit, sort="new", limit=half
            )
            posts.extend(new_posts)
        except Exception as e:
            logger.warning(f"Failed to fetch new posts from {subreddit}: {e}")
        
        # Deduplicate by ID
        seen = set()
        unique = []
        for p in posts:
            if p.id not in seen:
                seen.add(p.id)
                unique.append(p)
        
        return unique[:self.sample_size]

    async def _fetch_sample_posts_from_db(self, community: DiscoveredCommunity) -> List[RedditPost]:
        """Prefer DB samples (posts_raw) after candidate vetting backfill."""
        subreddit = str(community.name or "").lstrip("r/").lower()
        if not subreddit:
            return []

        metrics: dict = dict(community.metrics or {})
        vetting = metrics.get("vetting") or {}
        try:
            lookback_days = int(vetting.get("days") or 30)
        except Exception:
            lookback_days = 30
        lookback_days = max(1, min(365, lookback_days))

        rows = await self.db.execute(
            text(
                """
                SELECT
                  source_post_id,
                  COALESCE(title,'') AS title,
                  COALESCE(body,'') AS body,
                  COALESCE(score,0) AS score,
                  COALESCE(num_comments,0) AS num_comments,
                  EXTRACT(EPOCH FROM created_at) AS created_utc,
                  COALESCE(subreddit,'') AS subreddit
                FROM posts_raw
                WHERE is_current = true
                  AND lower(regexp_replace(subreddit, '^r/','')) = :sub
                  AND created_at >= NOW() - (:days * INTERVAL '1 day')
                ORDER BY score DESC, created_at DESC
                LIMIT :limit
                """
            ),
            {"sub": subreddit, "days": int(lookback_days), "limit": int(self.sample_size)},
        )

        posts: List[RedditPost] = []
        for r in rows.mappings().all():
            pid = str(r.get("source_post_id") or "")
            if not pid:
                continue
            posts.append(
                RedditPost(
                    id=pid,
                    title=str(r.get("title") or ""),
                    selftext=str(r.get("body") or ""),
                    score=int(r.get("score") or 0),
                    num_comments=int(r.get("num_comments") or 0),
                    created_utc=float(r.get("created_utc") or 0.0),
                    subreddit=str(r.get("subreddit") or community.name or ""),
                    author="",
                    url="",
                    permalink="",
                )
            )
        return posts[: self.sample_size]

    async def _approve_community(
        self,
        community: DiscoveredCommunity,
        value_density: float,
        breakdown: dict,
        sample_size: int,
        high_value_count: int,
    ) -> dict:
        """Approve a community and add to CommunityPool."""
        now = datetime.now(timezone.utc)

        # Hard gate: never auto-activate a community that is already blacklisted in the pool.
        pool_row = await self.db.execute(
            select(CommunityPool.is_blacklisted).where(CommunityPool.name == community.name)
        )
        if pool_row.scalar_one_or_none() is True:
            community.status = "blacklisted"
            community.admin_reviewed_at = now
            community.admin_notes = (
                (community.admin_notes or "").strip() + "\nblocked: community_pool is_blacklisted=true"
            ).strip()
            base_metrics = dict(community.metrics or {})
            base_metrics["evaluation"] = {
                "blocked_by_pool_blacklist": True,
                "evaluated_at": now.isoformat(),
            }
            community.metrics = base_metrics
            await self.db.commit()
            logger.warning("🚫 Blocked approval: %s is blacklisted in community_pool", community.name)
            return {
                "community": community.name,
                "status": "blacklisted",
                "message": "blocked: community_pool is_blacklisted=true",
            }

        # Update discovered_communities status (merge metrics; don't erase vetting/warzone fields)
        community.status = "approved"
        community.admin_reviewed_at = now
        base_metrics = dict(community.metrics or {})
        base_metrics["evaluation"] = {
            "value_density": value_density,
            "breakdown": breakdown,
            "sample_size": sample_size,
            "high_value_count": high_value_count,
            "evaluated_at": now.isoformat(),
        }
        community.metrics = base_metrics

        # Create CommunityPool entry (if not exists)
        await self.db.execute(
            text("""
                INSERT INTO community_pool (
                    name,
                    tier,
                    is_active,
                    categories,
                    description_keywords,
                    semantic_quality_score,
                    created_at,
                    updated_at
                )
                VALUES (:name, 'medium', true, '{}', '{}'::jsonb, :quality, :now, :now)
                ON CONFLICT (name) DO UPDATE SET
                    is_active = true,
                    tier = 'medium',
                    updated_at = :now
                WHERE community_pool.is_blacklisted IS FALSE
            """),
            {"name": community.name, "now": now, "quality": float(value_density)}
        )

        await self.db.commit()
        
        logger.info(f"✅ Approved {community.name} with density {value_density:.1%}")
        
        return {
            "community": community.name,
            "status": "approved",
            "value_density": value_density,
            "sample_size": sample_size,
            "high_value_count": high_value_count,
            "breakdown": breakdown,
            "message": f"Community approved with {value_density:.1%} value density",
        }

    async def _reject_community(
        self,
        community: DiscoveredCommunity,
        value_density: float,
        breakdown: dict,
        reason: str,
    ) -> dict:
        """Reject a community with cooldown or blacklist."""
        now = datetime.now(timezone.utc)
        
        community.rejection_count += 1
        community.cooldown_until = now + timedelta(days=COOLDOWN_DAYS)
        base_metrics = dict(community.metrics or {})
        base_metrics["evaluation"] = {
            "value_density": value_density,
            "breakdown": breakdown,
            "rejection_reason": reason,
            "evaluated_at": now.isoformat(),
        }
        community.metrics = base_metrics

        if community.rejection_count >= MAX_REJECTIONS:
            community.status = "blacklisted"
            community.admin_notes = f"Auto-blacklisted after {MAX_REJECTIONS} rejections"
            logger.warning(f"🚫 Blacklisted {community.name} after {MAX_REJECTIONS} rejections")
            status = "blacklisted"
            message = f"Community blacklisted after {MAX_REJECTIONS} rejections"
        else:
            community.status = "rejected"
            logger.info(f"❌ Rejected {community.name} (attempt {community.rejection_count})")
            status = "rejected"
            message = f"Rejected ({community.rejection_count}/{MAX_REJECTIONS}). Cooldown until {community.cooldown_until}"

        await self.db.commit()
        
        return {
            "community": community.name,
            "status": status,
            "value_density": value_density,
            "rejection_count": community.rejection_count,
            "cooldown_until": community.cooldown_until.isoformat() if community.cooldown_until else None,
            "breakdown": breakdown,
            "message": message,
        }

    async def evaluate_all_pending(self) -> List[dict]:
        """Evaluate all pending communities that are not in cooldown.
        
        Returns:
            List of evaluation results
        """
        now = datetime.now(timezone.utc)
        
        stmt = select(DiscoveredCommunity).where(
            DiscoveredCommunity.status == "pending",
            (DiscoveredCommunity.cooldown_until.is_(None)) | 
            (DiscoveredCommunity.cooldown_until <= now)
        ).order_by(DiscoveredCommunity.discovered_count.desc())
        
        result = await self.db.execute(stmt)
        communities = result.scalars().all()
        
        results = []
        for community in communities:
            result = await self.evaluate(community.name)
            results.append(result)
        
        return results


__all__ = ["CommunityEvaluator"]
