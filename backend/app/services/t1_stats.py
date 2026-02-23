"""T1 Stats Layer: 聚合社区活跃度、P/S 比、痛点分布、品牌共现."""
from __future__ import annotations

import json
from collections import defaultdict, Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.semantic.embedding_service import embedding_service
from app.db.read_scopes import get_comments_core_lab_relation

@dataclass(slots=True)
class CommunityStat:
    subreddit: str
    posts: int
    comments: int
    ps_ratio: Optional[float]
    pain_count: int
    solution_count: int
    recent_posts_30d: int
    recent_comments_30d: int

@dataclass(slots=True)
class AspectBreakdown:
    aspect: str
    pain: int
    total: int

    @property
    def pain_ratio(self) -> float:
        denom = max(1, self.total)
        return round(self.pain / denom, 4)

@dataclass(slots=True)
class BrandPainCooccurrence:
    brand: str
    mentions: int
    aspects: list[str]
    unique_authors: int
    evidence_comment_ids: list[str]

@dataclass(slots=True)
class T1StatsSnapshot:
    generated_at: str
    since_utc: str
    subreddits: list[str]
    global_ps_ratio: Optional[float]
    total_pain: int
    total_solution: int
    community_stats: list[CommunityStat]
    aspect_breakdown: list[AspectBreakdown]
    brand_pain_cooccurrence: list[BrandPainCooccurrence]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "since_utc": self.since_utc,
            "subreddits": self.subreddits,
            "global_ps_ratio": self.global_ps_ratio,
            "total_pain": self.total_pain,
            "total_solution": self.total_solution,
            "community_stats": [asdict(c) for c in self.community_stats],
            "aspect_breakdown": [
                {**asdict(a), "pain_ratio": a.pain_ratio} for a in self.aspect_breakdown
            ],
            "brand_pain_cooccurrence": [asdict(b) for b in self.brand_pain_cooccurrence],
        }


class T1StatsService:
    """
    Service layer for T1 Statistics.
    Adapts raw snapshots into format needed by ReportAgent.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_overview_stats(self, days: int = 365) -> dict[str, Any]:
        """
        Returns high-level stats for the report header and decision card.
        """
        snapshot = await build_stats_snapshot(self.session, days=days)
        
        # Calculate aggregates
        total_posts = sum(c.posts for c in snapshot.community_stats)
        total_comments = sum(c.comments for c in snapshot.community_stats)
        
        # Prepare top communities with richer info (mocking keywords/sample for now if not in stats)
        # In a real scenario, we might want to fetch keywords here or join with other tables.
        # For now, we will let the Agent fetch keywords or use placeholders if not available.
        # However, to support the new prompt, we need keywords.
        # Let's do a quick fetch for top keywords for top communities.
        
        top_comms = []
        for c in snapshot.community_stats[:5]: # Top 5
            # Fetch sample title & keywords
            keywords = await self._fetch_community_keywords(c.subreddit)
            sample = await self._fetch_sample_title(c.subreddit)
            
            top_comms.append({
                "name": c.subreddit,
                "posts": c.posts,
                "comments": c.comments,
                "top_keywords": keywords,
                "sample_title": sample
            })

        return {
            "community_count": len(snapshot.subreddits),
            "total_posts": total_posts,
            "total_comments": total_comments,
            "ps_ratio": snapshot.global_ps_ratio or 1.0,
            "top_communities": top_comms,
            "raw_snapshot": snapshot
        }

    async def _fetch_community_keywords(self, subreddit: str) -> list[str]:
        # Quick hack: get keywords from community pool description or just use static ones
        # Better: query semantic terms frequency? 
        # For speed, let's query description_keywords from pool if available, 
        # or just return some generics.
        sql = "SELECT description_keywords FROM community_pool WHERE lower(name) = lower(:name)"
        res = await self.session.execute(text(sql), {"name": "r/"+subreddit if not subreddit.startswith("r/") else subreddit})
        row = res.fetchone()
        if row and row.description_keywords:
            return row.description_keywords
        return ["General Discussion", "Business"]

    async def _fetch_sample_title(self, subreddit: str) -> str:
        # Get one recent high-engagement post title
        sql = """
        SELECT title FROM posts_raw 
        WHERE lower(subreddit) = lower(:name) 
          AND is_current = true
          AND created_at >= NOW() - INTERVAL '1 year'
        ORDER BY created_at DESC 
        LIMIT 1
        """
        res = await self.session.execute(text(sql), {"name": "r/"+subreddit if not subreddit.startswith("r/") else subreddit})
        row = res.fetchone()
        return row.title if row else "No recent posts"


# --- Internal Logic (Kept from original file) ---

async def _fetch_t1_subreddits(session: AsyncSession) -> list[str]:
    sql = """
    SELECT lower(name) AS name
    FROM community_pool
    WHERE tier = 'high' AND is_active = true AND deleted_at IS NULL
    ORDER BY name
    """
    rows = (await session.execute(text(sql))).scalars().all()
    # Do not strip r/ prefix, as posts_raw/comments store it
    return [r.lower() for r in rows]


async def _fetch_posts_comments(
    session: AsyncSession, *, subs: Sequence[str], since_dt: datetime
) -> Mapping[str, tuple[int, int, int, int]]:
    comments_rel = await get_comments_core_lab_relation(session)
    sql = f"""
    WITH posts AS (
        SELECT lower(subreddit) AS sr, COUNT(*) AS post_cnt,
               COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') AS recent_posts_30d
        FROM posts_raw
        WHERE is_current = true
          AND COALESCE(is_duplicate, false) = false
          AND created_at >= :since
          AND (:has_subs = FALSE OR lower(subreddit) = ANY(:subs))
        GROUP BY sr
    ),
    comments AS (
        SELECT lower(subreddit) AS sr, COUNT(*) AS comment_cnt,
               COUNT(*) FILTER (WHERE created_utc >= NOW() - INTERVAL '30 days') AS recent_comments_30d
        FROM {comments_rel}
        WHERE created_utc >= :since
          AND (:has_subs = FALSE OR lower(subreddit) = ANY(:subs))
        GROUP BY sr
    )
    SELECT COALESCE(p.sr, c.sr) AS subreddit,
           COALESCE(p.post_cnt, 0) AS posts,
           COALESCE(c.comment_cnt, 0) AS comments,
           COALESCE(p.recent_posts_30d, 0) AS recent_posts_30d,
           COALESCE(c.recent_comments_30d, 0) AS recent_comments_30d
    FROM posts p
    FULL OUTER JOIN comments c ON p.sr = c.sr
    """
    rows = await session.execute(
        text(sql),
        {
            "since": since_dt,
            "subs": list(subs) or [""],
            "has_subs": bool(subs),
        },
    )
    return {
        row.subreddit: (
            int(row.posts),
            int(row.comments),
            int(row.recent_posts_30d),
            int(row.recent_comments_30d),
        )
        for row in rows.fetchall()
    }


async def _fetch_ps_ratio_by_sub(
    session: AsyncSession, *, subs: Sequence[str], since_dt: datetime
) -> dict[str, tuple[int, int]]:
    comments_rel = await get_comments_core_lab_relation(session)
    sql = f"""
    WITH target_comments AS (
        SELECT id, lower(subreddit) AS sr
        FROM {comments_rel}
        WHERE created_utc >= :since
          AND (:has_subs = FALSE OR lower(subreddit) = ANY(:subs))
    ),
    counts AS (
        SELECT
            tc.sr AS subreddit,
            SUM(CASE WHEN cl.category = 'pain' THEN 1 ELSE 0 END) AS pain_cnt,
            SUM(CASE WHEN cl.category = 'solution' THEN 1 ELSE 0 END) AS sol_cnt
        FROM target_comments tc
        JOIN content_labels cl ON cl.content_type = 'comment' AND cl.content_id = tc.id
        GROUP BY tc.sr
    )
    SELECT subreddit, pain_cnt, sol_cnt FROM counts
    """
    rows = await session.execute(
        text(sql),
        {
            "since": since_dt,
            "subs": list(subs) or [""],
            "has_subs": bool(subs),
        },
    )
    return {
        row.subreddit: (int(row.pain_cnt or 0), int(row.sol_cnt or 0))
        for row in rows.fetchall()
    }


async def _fetch_aspect_breakdown(
    session: AsyncSession, *, subs: Sequence[str], since_dt: datetime
) -> list[AspectBreakdown]:
    comments_rel = await get_comments_core_lab_relation(session)
    sql = f"""
    WITH target_comments AS (
        SELECT id
        FROM {comments_rel}
        WHERE created_utc >= :since
          AND (:has_subs = FALSE OR lower(subreddit) = ANY(:subs))
    )
    SELECT cl.aspect AS aspect,
           COUNT(*) AS pain_cnt,
           COUNT(*) AS total_cnt
    FROM content_labels cl
    JOIN target_comments tc ON cl.content_id = tc.id AND cl.content_type = 'comment'
    WHERE cl.category = 'pain'
    GROUP BY cl.aspect
    ORDER BY pain_cnt DESC
    """
    rows = await session.execute(
        text(sql),
        {
            "since": since_dt,
            "subs": list(subs) or [""],
            "has_subs": bool(subs),
        },
    )
    return [
        AspectBreakdown(aspect=row.aspect, pain=int(row.pain_cnt or 0), total=int(row.total_cnt or 0))
        for row in rows.fetchall()
    ]


async def _fetch_brand_pain_cooccurrence(
    session: AsyncSession,
    *,
    subs: Sequence[str],
    since_dt: datetime,
    limit: int = 10,
) -> list[BrandPainCooccurrence]:
    comments_rel = await get_comments_core_lab_relation(session)
    sql = f"""
    WITH target_comments AS (
        SELECT id, reddit_comment_id, author_name
        FROM {comments_rel}
        WHERE created_utc >= :since
          AND (:has_subs = FALSE OR lower(subreddit) = ANY(:subs))
    ),
    pain_comments AS (
        SELECT cl.content_id AS comment_id, cl.aspect AS aspect
        FROM content_labels cl
        JOIN target_comments tc ON tc.id = cl.content_id
        WHERE cl.content_type = 'comment' AND cl.category = 'pain'
    ),
    brand_entities AS (
        SELECT ce.content_id AS comment_id, ce.entity AS brand
        FROM content_entities ce
        JOIN target_comments tc ON tc.id = ce.content_id
        WHERE ce.content_type = 'comment' AND ce.entity_type = 'brand'
    ),
    joined AS (
        SELECT b.brand AS brand, p.aspect AS aspect, p.comment_id
        FROM pain_comments p
        JOIN brand_entities b ON b.comment_id = p.comment_id
    )
    SELECT brand,
           COUNT(*) AS mentions,
           ARRAY_AGG(DISTINCT aspect) AS aspects,
           COUNT(DISTINCT tc.author_name) AS unique_authors,
           ARRAY_AGG(DISTINCT tc.reddit_comment_id) AS evidence_comment_ids
    FROM joined
    JOIN target_comments tc ON tc.id = joined.comment_id
    GROUP BY brand
    ORDER BY mentions DESC
    LIMIT :limit
    """
    rows = await session.execute(
        text(sql),
        {
            "since": since_dt,
            "subs": list(subs) or [""],
            "has_subs": bool(subs),
            "limit": limit,
        },
    )
    results: list[BrandPainCooccurrence] = []
    for row in rows.fetchall():
        aspects: list[str] = []
        if isinstance(row.aspects, Iterable):
            aspects = [str(a) for a in row.aspects if a]
        results.append(
            BrandPainCooccurrence(
                brand=row.brand,
                mentions=int(row.mentions or 0),
                aspects=aspects,
                unique_authors=int(row.unique_authors or 0),
                evidence_comment_ids=[str(cid) for cid in (row.evidence_comment_ids or []) if cid],
            )
        )
    return results


async def build_trend_analysis(
    session: AsyncSession,
    *,
    topic_tokens: Sequence[str],
    months: int = 12,
) -> list[dict[str, Any]]:
    """
    Compute monthly trend for keywords across posts_raw + comments.

    Returns list of dicts sorted by month asc:
    [
        {"month": "2024-11", "count": 1250, "growth_rate": 0.45, "trend": "📈 RISING"},
        ...
    ]
    """
    tokens = [t.strip().lower() for t in topic_tokens or [] if t and t.strip()]
    if not tokens:
        return []

    comments_rel = await get_comments_core_lab_relation(session)
    sql = """
    WITH months AS (
        SELECT date_trunc('month', CURRENT_DATE) - (interval '1 month' * generate_series(0, :months - 1)) AS month_start
    ),
    posts AS (
        SELECT date_trunc('month', created_at) AS m, COUNT(*) AS cnt
        FROM posts_raw
        WHERE created_at >= (SELECT min(month_start) FROM months)
          AND COALESCE(is_duplicate, false) = false
          AND (
            {post_predicate}
          )
        GROUP BY m
    ),
    comments AS (
        SELECT date_trunc('month', created_utc) AS m, COUNT(*) AS cnt
        FROM {comments_rel}
        WHERE created_utc >= (SELECT min(month_start) FROM months)
          AND (
            {comment_predicate}
          )
        GROUP BY m
    ),
    merged AS (
        SELECT m AS month_start, SUM(cnt) AS cnt
        FROM (
            SELECT m, cnt FROM posts
            UNION ALL
            SELECT m, cnt FROM comments
        ) s
        GROUP BY m
    )
    SELECT to_char(months.month_start, 'YYYY-MM') AS month_key,
           COALESCE(cnt, 0) AS cnt
    FROM months
    LEFT JOIN merged ON months.month_start = merged.month_start
    ORDER BY months.month_start ASC
    """

    search_query = " | ".join(tokens)
    params: dict[str, Any] = {"months": months, "search_query": search_query}

    post_predicates = "to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(body, '')) @@ to_tsquery('english', :search_query)"
    comment_predicates = "to_tsvector('english', COALESCE(body, '')) @@ to_tsquery('english', :search_query)"

    stmt = text(
        sql.format(
            comments_rel=comments_rel,
            post_predicate=post_predicates,
            comment_predicate=comment_predicates,
        )
    )
    rows = await session.execute(stmt, params)
    series = [{"month": row.month_key, "count": int(row.cnt or 0)} for row in rows.fetchall()]

    # Calculate growth and trend labels
    results: list[dict[str, Any]] = []
    
    # Pre-calculate velocity metric: Volume(Last 30 Days) / Volume(Last 90 Days)
    # Using the last 3 entries if available
    recent_velocity = 1.0
    if len(series) >= 3:
        l30 = series[-1]["count"]
        # Approximate L90 by summing last 3 months
        l90 = sum(s["count"] for s in series[-3:])
        if l90 > 0:
            # Normalized velocity: If steady state, L30 should be ~1/3 of L90.
            # So Velocity = L30 / (L90 / 3) = 3 * L30 / L90
            recent_velocity = (3.0 * l30) / l90

    prev = None
    for entry in series:
        cnt = entry["count"]
        if prev is None or prev == 0:
            growth = None if prev is None else (cnt - prev) / max(1, prev)
        else:
            growth = (cnt - prev) / prev

        if growth is None:
            trend_label = "➡️ STABLE"
        # Combine monthly growth AND recent velocity for EXPLODING
        elif (growth > 0.5 and cnt > 5) or (recent_velocity > 1.3 and cnt > 10):
            trend_label = "🔥 EXPLODING"
        elif growth > 0.2 or recent_velocity > 1.1:
            trend_label = "📈 RISING"
        elif growth < -0.2 or recent_velocity < 0.8:
            trend_label = "📉 FALLING"
        else:
            trend_label = "➡️ STABLE"

        results.append(
            {
                "month": entry["month"],
                "count": cnt,
                "growth_rate": None if growth is None else round(growth, 4),
                "trend": trend_label,
            }
        )
        prev = cnt
    
    # Inject velocity into the last entry for debugging/frontend usage
    if results:
        results[-1]["recent_velocity"] = round(recent_velocity, 2)

    return results


async def build_entity_sentiment_matrix(
    session: AsyncSession,
    *,
    topic_tokens: Sequence[str],
    months: int = 12,
    min_mentions: int = 3,
) -> dict[str, dict[str, float]]:
    """
    Returns a nested dict: { "Entity": { "Aspect": score, ... }, ... }
    Score between -1.0 (negative) and 1.0 (positive).
    """
    tokens = [t.strip().lower() for t in topic_tokens or [] if t and t.strip()]
    if not tokens:
        return {}

    search_query = " | ".join(tokens)
    comments_rel = await get_comments_core_lab_relation(session)
    sql = f"""
    WITH relevant_comments AS (
        SELECT id
        FROM {comments_rel}
        WHERE created_utc >= NOW() - (interval '1 month' * :months)
          AND to_tsvector('english', COALESCE(body, '')) @@ to_tsquery('english', :search_query)
    )
    SELECT 
        e.entity_name,
        l.aspect,
        COUNT(*) as cnt,
        AVG(
            CASE 
                WHEN l.sentiment = 'positive' THEN 1.0 
                WHEN l.sentiment = 'negative' THEN -1.0 
                ELSE 0.0 
            END
        ) as score
    FROM relevant_comments c
    JOIN mv_analysis_entities e ON c.id = e.post_id
    JOIN mv_analysis_labels l ON c.id = l.post_id
    WHERE e.entity_type = 'brand'
    GROUP BY e.entity_name, l.aspect
    HAVING COUNT(*) >= :min_mentions
    ORDER BY cnt DESC
    """
    params = {
        "months": months,
        "search_query": search_query,
        "min_mentions": min_mentions,
    }
    rows = await session.execute(text(sql), params)
    matrix: dict[str, dict[str, float]] = {}
    for row in rows.fetchall():
        entity = getattr(row, "entity_name", None)
        aspect = getattr(row, "aspect", None)
        score = getattr(row, "score", None)
        if not entity or aspect is None:
            continue
        if entity not in matrix:
            matrix[entity] = {}
        matrix[entity][aspect] = float(score) if score is not None else 0.0
    return matrix


async def fetch_topic_relevant_communities(
    session: AsyncSession,
    *,
    topic: str,  # [NEW] Raw topic for semantic search
    topic_tokens: Sequence[str],
    exclusion_tokens: Sequence[str] | None = None,
    days: int = 365,
    min_relevance_score: int = 5,
) -> dict[str, int]:
    """按内容相关性统计社区，过滤掉噪音社区。

    支持：
    1. 关键词匹配 (to_tsvector)
    2. 语义向量匹配 (embedding <=> topic_embedding)

    返回 {subreddit: count}，仅包含 count >= min_relevance_score 的社区。
    """
    tokens = [t.strip().lower() for t in topic_tokens or [] if t and t.strip()]
    if not tokens:
        return {}
    search_query = " | ".join(tokens)

    # [NEW] Generate topic embedding
    try:
        topic_embedding = embedding_service.encode(topic)
        has_embedding = True
    except Exception as e:
        print(f"⚠️ Semantic embedding failed: {e}")
        topic_embedding = None
        has_embedding = False

    excludes = [e.strip().lower() for e in (exclusion_tokens or []) if e and e.strip()]
    exclude_query = " | ".join(excludes)
    has_exclude = bool(exclude_query)

    # Comments 查询容易超时，窗口缩短到 180 天兜底
    comments_days = min(days, 180)

    params_common = {
        "days": days,
        "search_query": search_query,
        "has_exclude": has_exclude,
        "exclude_query": exclude_query or "''",
    }
    params_comments = {
        "days": comments_days,
        "search_query": search_query,
        "has_exclude": has_exclude,
        "exclude_query": exclude_query or "''",
    }

    counts: Counter[str] = Counter()

    # 1) 全文检索（GIN）
    sql_posts_fulltext = text(
        """
        SELECT lower(p.subreddit) AS sr, COUNT(*) AS cnt
        FROM posts_raw p
        WHERE p.created_at >= NOW() - (interval '1 day' * :days)
          AND p.created_at >= NOW() - INTERVAL '1 year'
          AND p.is_current = true
          AND COALESCE(p.is_duplicate, false) = false
          AND to_tsvector('english', COALESCE(p.title, '') || ' ' || COALESCE(p.body, ''))
              @@ to_tsquery('english', :search_query)
          AND (
              :has_exclude = FALSE OR NOT (
                  to_tsvector('english', COALESCE(p.title, '') || ' ' || COALESCE(p.body, ''))
                  @@ to_tsquery('english', :exclude_query)
              )
          )
        GROUP BY sr
        """
    )
    rows = await session.execute(sql_posts_fulltext, params_common)
    for row in rows.fetchall():
        sr = getattr(row, "sr", None)
        cnt = getattr(row, "cnt", 0) or 0
        if sr:
            counts[sr] += int(cnt)

    # 2) 语义匹配（向量索引）
    if has_embedding and topic_embedding is not None:
        # pgvector expects a string representation like '[1.0, 2.0]' for vector literals
        # when using simple bind parameters via SQLAlchemy/asyncpg
        topic_embedding_str = str(topic_embedding)
        
        sql_posts_semantic = text(
            """
            SELECT lower(p.subreddit) AS sr, COUNT(*) AS cnt
            FROM posts_raw p
            JOIN post_embeddings pe ON pe.post_id = p.id
            WHERE p.created_at >= NOW() - (interval '1 day' * :days)
              AND p.created_at >= NOW() - INTERVAL '1 year'
              AND p.is_current = true
              AND COALESCE(p.is_duplicate, false) = false
              AND pe.embedding <=> :topic_embedding < 0.4
            GROUP BY sr
            """
        )
        rows = await session.execute(
            sql_posts_semantic,
            {"days": days, "topic_embedding": topic_embedding_str},
        )
    for row in rows.fetchall():
        sr = getattr(row, "sr", None)
        cnt = getattr(row, "cnt", 0) or 0
        if sr:
            counts[sr] += int(cnt)

    # 3) 评论全文检索
    comments_rel = await get_comments_core_lab_relation(session)
    sql_comments_fulltext = text(
        f"""
        SELECT lower(subreddit) AS sr, COUNT(*) AS cnt
        FROM {comments_rel}
        WHERE created_utc >= NOW() - (interval '1 day' * :days)
          AND created_utc >= NOW() - INTERVAL '1 year'
          AND to_tsvector('english', COALESCE(body, ''))
              @@ to_tsquery('english', :search_query)
          AND (
              :has_exclude = FALSE OR NOT (
                  to_tsvector('english', COALESCE(body, ''))
                  @@ to_tsquery('english', :exclude_query)
              )
          )
        GROUP BY sr
        """
    )
    rows = await session.execute(sql_comments_fulltext, params_comments)
    for row in rows.fetchall():
        sr = getattr(row, "sr", None)
        cnt = getattr(row, "cnt", 0) or 0
        if sr:
            counts[sr] += int(cnt)

    return {sr: int(cnt) for sr, cnt in counts.items() if cnt >= min_relevance_score}
async def build_stats_snapshot(
    session: AsyncSession,
    *,
    subreddits: Optional[Sequence[str]] = None,
    days: int = 365,
    brand_limit: int = 10,
) -> T1StatsSnapshot:
    since_dt = datetime.now(timezone.utc) - timedelta(days=min(365, max(1, days)))
    # Do not remove prefix, just lower
    subs = list({s.lower() for s in (subreddits or []) if s}) or await _fetch_t1_subreddits(session)

    posts_comments = await _fetch_posts_comments(session, subs=subs, since_dt=since_dt)
    ps_counts = await _fetch_ps_ratio_by_sub(session, subs=subs, since_dt=since_dt)

    community_stats: list[CommunityStat] = []
    total_pain = 0
    total_sol = 0
    for sr in subs:
        posts, comments, recent_posts_30d, recent_comments_30d = posts_comments.get(sr, (0, 0, 0, 0))
        pain_cnt, sol_cnt = ps_counts.get(sr, (0, 0))
        total_pain += pain_cnt
        total_sol += sol_cnt
        denom = max(1, sol_cnt)
        community_stats.append(
            CommunityStat(
                subreddit=sr,
                posts=posts,
                comments=comments,
                recent_posts_30d=recent_posts_30d,
                recent_comments_30d=recent_comments_30d,
                ps_ratio=(float(pain_cnt) / float(denom)) if (pain_cnt + sol_cnt) > 0 else None,
                pain_count=pain_cnt,
                solution_count=sol_cnt,
            )
        )

    global_ps_ratio = None
    if total_pain + total_sol > 0:
        global_ps_ratio = float(total_pain) / float(max(1, total_sol))

    aspect_breakdown = await _fetch_aspect_breakdown(session, subs=subs, since_dt=since_dt)
    brand_pain = await _fetch_brand_pain_cooccurrence(
        session, subs=subs, since_dt=since_dt, limit=brand_limit
    )

    return T1StatsSnapshot(
        generated_at=datetime.now(timezone.utc).isoformat(),
        since_utc=since_dt.isoformat(),
        subreddits=subs,
        global_ps_ratio=global_ps_ratio,
        total_pain=total_pain,
        total_solution=total_sol,
        community_stats=sorted(community_stats, key=lambda x: x.comments, reverse=True),
        aspect_breakdown=aspect_breakdown,
        brand_pain_cooccurrence=brand_pain,
    )


async def write_snapshot_to_file(
    session: AsyncSession,
    output_path: Path = Path("reports/local-acceptance/t1-stats-snapshot.json"),
    *,
    subreddits: Optional[Sequence[str]] = None,
    days: int = 365,
    brand_limit: int = 10,
) -> Path:
    snapshot = await build_stats_snapshot(
        session, subreddits=subreddits, days=days, brand_limit=brand_limit
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


__all__ = [
    "T1StatsService",
    "T1StatsSnapshot",
    "CommunityStat",
    "AspectBreakdown",
    "BrandPainCooccurrence",
    "build_stats_snapshot",
    "write_snapshot_to_file",
    "build_trend_analysis",
    "build_entity_sentiment_matrix",
    "fetch_topic_relevant_communities",
]
