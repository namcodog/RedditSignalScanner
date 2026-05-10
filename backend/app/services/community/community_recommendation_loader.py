from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.community.community_recommendation_models import CommunitySignal
from app.services.community.community_recommendation_utils import (
    flatten_json_values,
    is_within_15d,
    latest_activity,
)
from app.services.hotpost.hotpost_community_activity import (
    HotpostCommunityActivityProvider,
    normalize_community_key,
)


async def load_community_signals(
    session: AsyncSession,
    *,
    activity_provider: HotpostCommunityActivityProvider | None = None,
) -> tuple[CommunitySignal, ...]:
    activity_provider = activity_provider or HotpostCommunityActivityProvider()
    hotpost_activity = await activity_provider.load(session)
    result = await session.execute(text(_COMMUNITY_SIGNAL_SQL))
    signals: list[CommunitySignal] = []
    for row in result.mappings().all():
        key = normalize_community_key(row["name"])
        activity = hotpost_activity.get(key)
        source_refs = _source_refs_for_activity(activity)
        hotpost_cards = int(activity.card_count if activity else 0)
        latest = row["latest_activity_at"].isoformat() if row["latest_activity_at"] is not None else None
        recent_posts = int(row["recent_posts_15d"] or 0)
        recent_source = "db_posts_hot_15d" if recent_posts else None
        if activity and is_within_15d(activity.latest_card_at):
            recent_posts = max(recent_posts, 1)
            latest = latest_activity(latest, activity.latest_card_at)
            recent_source = "hotpost_recent_probe"
        signals.append(
            CommunitySignal(
                community=str(row["name"]),
                categories=tuple(str(item) for item in flatten_json_values(row["categories"])),
                keywords=tuple(str(item) for item in flatten_json_values(row["description_keywords"])),
                semantic_terms=tuple(str(item) for item in flatten_json_values(row["semantic_terms"])[:5]),
                source_refs=source_refs,
                content_label_terms=tuple(str(item) for item in flatten_json_values(row["label_terms"])[:5]),
                content_entity_terms=tuple(str(item) for item in flatten_json_values(row["entity_terms"])[:5]),
                semantic_observations=int(row["semantic_observations"] or 0),
                historical_posts=int(row["historical_posts"] or 0),
                recent_posts_15d=recent_posts,
                latest_activity_at=latest,
                recent_activity_source=recent_source,
                hotpost_cards=hotpost_cards,
                content_labels=int(row["content_labels"] or 0),
                content_entities=int(row["content_entities"] or 0),
                quality_score=float(row["semantic_quality_score"] or 0.0),
                sample_titles=tuple(activity.example_titles if activity else ())[:3],
            )
        )
    return tuple(signals)


def _source_refs_for_activity(activity: object) -> tuple[str, ...]:
    if activity is None:
        return ()
    refs: list[str] = []
    for pack_id in getattr(activity, "topic_packs", {}):
        refs.append(f"topic_pack:{pack_id}")
    for cluster_id in getattr(activity, "topic_clusters", {}):
        refs.append(f"topic_cluster:{cluster_id}")
    return tuple(dict.fromkeys(refs))


_COMMUNITY_SIGNAL_SQL = """
WITH post_counts AS (
  SELECT lower(regexp_replace(subreddit, '^r/', '')) AS key,
         COUNT(*)::int AS historical_posts,
         COUNT(*) FILTER (WHERE created_at >= now() - interval '15 days')::int AS recent_posts_15d,
         MAX(created_at) AS latest_activity_at
  FROM posts_hot
  GROUP BY 1
), semantic_counts AS (
  SELECT lower(regexp_replace(ph.subreddit, '^r/', '')) AS key,
         COUNT(so.id)::int AS semantic_observations
  FROM posts_hot ph JOIN semantic_observation so
    ON so.content_type = 'post' AND so.content_id = ph.id
  GROUP BY 1
), label_counts AS (
  SELECT lower(regexp_replace(ph.subreddit, '^r/', '')) AS key,
         COUNT(cl.id)::int AS content_labels,
         array_agg(DISTINCT COALESCE(NULLIF(cl.aspect, ''), cl.category))
           FILTER (WHERE COALESCE(NULLIF(cl.aspect, ''), cl.category) IS NOT NULL) AS label_terms
  FROM posts_hot ph JOIN content_labels cl
    ON cl.content_type = 'post' AND cl.content_id = ph.id
  GROUP BY 1
), entity_counts AS (
  SELECT lower(regexp_replace(ph.subreddit, '^r/', '')) AS key,
         COUNT(ce.id)::int AS content_entities,
         array_agg(DISTINCT ce.entity) FILTER (WHERE ce.entity IS NOT NULL) AS entity_terms
  FROM posts_hot ph JOIN content_entities ce
    ON ce.content_type = 'post' AND ce.content_id = ph.id
  GROUP BY 1
), semantic_term_counts AS (
  SELECT lower(regexp_replace(ph.subreddit, '^r/', '')) AS key,
         array_agg(DISTINCT st.canonical) FILTER (WHERE st.canonical IS NOT NULL) AS semantic_terms
  FROM posts_hot ph
  JOIN semantic_observation so ON so.content_type = 'post' AND so.content_id = ph.id
  JOIN semantic_terms st ON st.id = so.term_id
  GROUP BY 1
)
SELECT cp.name, cp.categories, cp.description_keywords, cp.semantic_quality_score,
       COALESCE(pc.historical_posts, 0) AS historical_posts,
       COALESCE(pc.recent_posts_15d, 0) AS recent_posts_15d,
       pc.latest_activity_at,
       COALESCE(sc.semantic_observations, 0) AS semantic_observations,
       COALESCE(lc.content_labels, 0) AS content_labels,
       COALESCE(ec.content_entities, 0) AS content_entities,
       COALESCE(stc.semantic_terms, ARRAY[]::text[]) AS semantic_terms,
       COALESCE(lc.label_terms, ARRAY[]::text[]) AS label_terms,
       COALESCE(ec.entity_terms, ARRAY[]::text[]) AS entity_terms
FROM community_pool cp
LEFT JOIN post_counts pc ON pc.key = cp.name_key
LEFT JOIN semantic_counts sc ON sc.key = cp.name_key
LEFT JOIN label_counts lc ON lc.key = cp.name_key
LEFT JOIN entity_counts ec ON ec.key = cp.name_key
LEFT JOIN semantic_term_counts stc ON stc.key = cp.name_key
WHERE cp.deleted_at IS NULL AND cp.is_active IS TRUE AND cp.is_blacklisted IS FALSE
ORDER BY cp.name
"""
