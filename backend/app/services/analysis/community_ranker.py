from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.read_scopes import get_comments_core_lab_relation


async def _ps_ratio_by_subreddit(session: AsyncSession, subs: Sequence[str], since_days: int) -> Dict[str, float]:
    since = datetime.now(timezone.utc) - timedelta(days=max(1, since_days))
    comments_rel = await get_comments_core_lab_relation(session)
    res = await session.execute(
        text(
            f"""
            WITH target AS (
              SELECT lower(c.subreddit) AS sub, cl.category
              FROM {comments_rel} c
              JOIN content_labels cl ON cl.content_type='comment' AND cl.content_id = c.id
              WHERE c.created_utc >= :since AND (:has = FALSE OR lower(c.subreddit) = ANY(:subs))
            )
            SELECT sub,
                   SUM(CASE WHEN category='pain' THEN 1 ELSE 0 END)::float AS pains,
                   SUM(CASE WHEN category='solution' THEN 1 ELSE 0 END)::float AS sols
            FROM target
            GROUP BY sub
            """
        ),
        {"since": since, "has": bool(subs), "subs": [s.lower() for s in subs] or [""]},
    )
    out: Dict[str, float] = {}
    for sub, pains, sols in res.fetchall():
        p = float(pains or 0.0)
        s = float(sols or 0.0)
        if p == 0.0 and s == 0.0:
            out[str(sub)] = 0.0
        else:
            out[str(sub)] = p / max(1.0, s)
    return out


async def _pain_density(session: AsyncSession, subs: Sequence[str], since_days: int) -> Dict[str, float]:
    since = datetime.now(timezone.utc) - timedelta(days=max(1, since_days))
    comments_rel = await get_comments_core_lab_relation(session)
    res = await session.execute(
        text(
            f"""
            WITH base AS (
              SELECT lower(c.subreddit) AS sub, 1 AS cnt
              FROM {comments_rel} c WHERE c.created_utc >= :since AND (:has=FALSE OR lower(c.subreddit)=ANY(:subs))
            ), pain AS (
              SELECT lower(c.subreddit) AS sub, COUNT(*)::float AS pains
              FROM {comments_rel} c
              JOIN content_labels cl ON cl.content_type='comment' AND cl.content_id=c.id AND cl.category='pain'
              WHERE c.created_utc >= :since AND (:has=FALSE OR lower(c.subreddit)=ANY(:subs))
              GROUP BY lower(c.subreddit)
            )
            SELECT b.sub, COALESCE(p.pains, 0.0) / GREATEST(COUNT(b.cnt)::float, 1.0)
            FROM base b LEFT JOIN pain p ON p.sub=b.sub
            GROUP BY b.sub, p.pains
            """
        ),
        {"since": since, "has": bool(subs), "subs": [s.lower() for s in subs] or [""]},
    )
    return {str(sub): float(density or 0.0) for sub, density in res.fetchall()}


async def _brand_penetration(session: AsyncSession, subs: Sequence[str], since_days: int) -> Dict[str, float]:
    since = datetime.now(timezone.utc) - timedelta(days=max(1, since_days))
    comments_rel = await get_comments_core_lab_relation(session)
    res = await session.execute(
        text(
            f"""
            WITH comments_in AS (
              SELECT id, lower(subreddit) AS sub
              FROM {comments_rel}
              WHERE created_utc >= :since AND (:has=FALSE OR lower(subreddit)=ANY(:subs))
            ), brands AS (
              SELECT ci.sub AS sub, COUNT(DISTINCT ce.content_id)::float AS brand_mentioned
              FROM comments_in ci
              JOIN content_entities ce ON ce.content_type='comment' AND ce.content_id=ci.id AND ce.entity_type='brand'
              GROUP BY ci.sub
            )
            SELECT ci.sub,
                   COALESCE(b.brand_mentioned, 0.0) / GREATEST(COUNT(ci.id)::float, 1.0) AS penetration
            FROM comments_in ci LEFT JOIN brands b ON b.sub=ci.sub
            GROUP BY ci.sub, b.brand_mentioned
            """
        ),
        {"since": since, "has": bool(subs), "subs": [s.lower() for s in subs] or [""]},
    )
    return {str(sub): float(pen or 0.0) for sub, pen in res.fetchall()}


async def _moderation_score(session: AsyncSession, subs: Sequence[str]) -> Dict[str, float]:
    # Use latest snapshot if present; otherwise 0.5 baseline (50/100)
    res = await session.execute(
        text(
            """
            SELECT DISTINCT ON (lower(subreddit)) lower(subreddit) AS sub, moderation_score
            FROM subreddit_snapshots
            WHERE (:has=FALSE OR lower(subreddit)=ANY(:subs))
            ORDER BY lower(subreddit), captured_at DESC
            """
        ),
        {"has": bool(subs), "subs": [s.lower() for s in subs] or [""]},
    )
    out: Dict[str, float] = {}
    for sub, score in res.fetchall():
        try:
            out[str(sub)] = float(score or 50.0) / 100.0
        except Exception:
            out[str(sub)] = 0.5
    return out


async def _fetch_30d_counts(session: AsyncSession, subs: Sequence[str]) -> Dict[str, int]:
    since30 = datetime.now(timezone.utc) - timedelta(days=30)
    res = await session.execute(
        text(
            """
            SELECT lower(subreddit) AS sub, COUNT(*) AS c
            FROM posts_hot 
            WHERE created_at >= :since30 AND (:has=FALSE OR lower(subreddit)=ANY(:subs))
            GROUP BY lower(subreddit)
            """
        ),
        {"since30": since30, "has": bool(subs), "subs": [s.lower() for s in subs] or [""]},
    )
    return {str(sub): int(r or 0) for sub, r in res.fetchall()}


async def _growth_7_over_30(session: AsyncSession, subs: Sequence[str]) -> Dict[str, float]:
    now = datetime.now(timezone.utc)
    since7 = now - timedelta(days=7)
    counts_30 = await _fetch_30d_counts(session, subs)
    
    res = await session.execute(
        text(
            """
            SELECT lower(subreddit) AS sub, COUNT(*)::float AS c
            FROM posts_hot WHERE created_at >= :since7 AND (:has=FALSE OR lower(subreddit)=ANY(:subs))
            GROUP BY lower(subreddit)
            """
        ),
        {"since7": since7, "has": bool(subs), "subs": [s.lower() for s in subs] or [""]},
    )
    counts_7 = {str(sub): float(r or 0.0) for sub, r in res.fetchall()}
    
    growth: Dict[str, float] = {}
    for sub in subs:
        key = sub.lower()
        c7 = counts_7.get(key, 0.0)
        c30 = float(counts_30.get(key, 0.0))
        growth[key] = c7 / max(c30 / 4.0, 1.0)
    return growth


def _norm(v: float, cap: float = 1.0) -> float:
    try:
        x = float(v)
    except Exception:
        return 0.0
    if cap > 0:
        x = min(x, cap)
    return max(0.0, x)


import math

async def compute_ranking_scores(
    session: AsyncSession,
    subreddits: Iterable[str],
    *,
    relevance_map: Dict[str, int] | None = None,
    since_days_7: int = 7,
    since_days_30: int = 30,
    topic_tokens: Iterable[str] | None = None,
) -> Dict[str, float]:
    """Compute 'Signal Density Score' for communities.

    New Algorithm (SignalDensityScore):
    Prioritizes communities that are highly concentrated on the topic, 
    while using Log Smoothing to ensure enough volume without letting
    massive generic subreddits dominate.

    Factors:
      1. Signal Density (30%): (Topic Hits) / (Total Posts + 10). 
         - The +10 smoothing penalizes tiny samples (1/1 != 100/100).
      2. Name Relevance (30%): Does the subreddit name contain the topic?
         - Essential for finding "Vertical Communities" (e.g. r/espresso).
      3. Pain Intensity (20%): Normalized P/S Ratio.
      4. Relevant Volume (10%): Log10(Topic Hits + 1).
         - Diminishing returns on volume. 100 posts is much better than 10, 
           but 10,000 is not 100x better than 100.
      5. Brand Penetration (10%): Presence of entities.
    """
    subs = list(subreddits)
    if not subs:
        return {}

    # Fetch Metrics
    ps = await _ps_ratio_by_subreddit(session, subs, since_days_30)
    density = await _pain_density(session, subs, since_days_30) # Used as secondary pain metric
    brand = await _brand_penetration(session, subs, since_days_30)
    mod = await _moderation_score(session, subs)
    
    # Fetch Base Volume (Total Posts in 30d)
    total_counts = await _fetch_30d_counts(session, subs)
    
    # Prepare Name Matching Set
    match_tokens = set()
    if topic_tokens:
        match_tokens = {t.lower() for t in topic_tokens if len(t) > 2}
    
    scores: Dict[str, float] = {}
    
    # Calculate Scores
    for s in subs:
        key = s.lower()
        sub_name_clean = key.replace("r/", "")
        
        # 1. Get Base Metrics
        topic_hits = relevance_map.get(key, 0) if relevance_map else 0
        total_posts = total_counts.get(key, 0)
        
        # 2. Signal Density (30%)
        # "Is this place ABOUT the topic?"
        # Smoothing (+10) prevents 1/1 posts from scoring 100% density
        sig_density = topic_hits / (total_posts + 10.0)
        # Cap density at 1.0 (though rare with smoothing)
        norm_density = min(sig_density, 1.0)
        
        # 3. Name Relevance (30%) - NEW
        # "Is the subreddit literally named after the topic?"
        norm_name = 0.0
        if match_tokens:
            for token in match_tokens:
                if token in sub_name_clean:
                    norm_name = 1.0
                    break
        
        # 4. Relevant Volume (10%)
        # "Is there enough data to matter?"
        # Log10 scale: 10 hits -> 1.0, 100 hits -> 2.0, 1000 hits -> 3.0
        # We normalize assuming ~1000 hits is "saturation" (score 1.0)
        vol_score = math.log10(topic_hits + 1)
        norm_volume = min(vol_score, 3.0) / 3.0
        
        # 5. Pain Intensity (20%)
        # "Are people complaining?"
        # Mix P/S Ratio and Pain Density
        raw_ps = ps.get(key, 0.0)
        raw_pd = density.get(key, 0.0)
        # P/S ratio > 2.0 is very high pain.
        norm_ps = min(raw_ps, 2.0) / 2.0
        # Pain density > 0.5 is very high.
        norm_pd = min(raw_pd, 0.5) / 0.5
        norm_pain = (norm_ps * 0.7) + (norm_pd * 0.3)
        
        # 6. Brand Penetration (10%)
        norm_brand = min(brand.get(key, 0.0), 1.0)
        
        # Final Weighted Score
        final_score = (
            0.30 * norm_density +
            0.30 * norm_name +
            0.20 * norm_pain +
            0.10 * norm_volume +
            0.10 * norm_brand
        )
        
        scores[s] = float(final_score)
        
    return scores


__all__ = ["compute_ranking_scores"]
