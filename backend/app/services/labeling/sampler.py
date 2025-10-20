"""Sampling utilities for Phase 3 labeling workflow."""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, MutableMapping, Sequence

import pandas as pd
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import SessionFactory
from app.models.posts_storage import PostRaw

SAMPLE_COLUMNS: List[str] = [
    "post_id",
    "title",
    "body",
    "subreddit",
    "score",
    "label",
    "strength",
    "notes",
]

_BUCKET_WEIGHTS: Dict[str, float] = {
    "very_low": 0.2,  # score < 10
    "low": 0.3,  # 10 <= score < 50
    "medium": 0.3,  # 50 <= score < 100
    "high": 0.2,  # score >= 100
}


def _assign_score_bucket(score: int) -> str:
    if score < 10:
        return "very_low"
    if score < 50:
        return "low"
    if score < 100:
        return "medium"
    return "high"


def _build_query(since: datetime, limit: int) -> Select[tuple[PostRaw]]:
    pool_size = max(limit * 5, 2000)
    return (
        select(PostRaw)
        .where(PostRaw.created_at >= since, PostRaw.is_current.is_(True))
        .order_by(PostRaw.created_at.desc())
        .limit(pool_size)
    )


def _normalise_record(record: PostRaw) -> Dict[str, Any]:
    score = int(record.score or 0)
    return {
        "post_id": record.source_post_id,
        "title": record.title or "",
        "body": record.body or "",
        "subreddit": record.subreddit or "",
        "score": score,
        "label": "",
        "strength": "",
        "notes": "",
        "_bucket": _assign_score_bucket(score),
        "_created_at": record.created_at or datetime.now(timezone.utc),
    }


def _derive_bucket_targets(
    *,
    limit: int,
    total_per_bucket: MutableMapping[str, int],
) -> Dict[str, int]:
    """Calculate how many samples to pick from each score bucket."""
    if limit <= 0:
        raise ValueError("limit must be positive")

    weighted_targets: Dict[str, int] = {}
    allocated = 0
    ordered_buckets = sorted(
        _BUCKET_WEIGHTS.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    for bucket, weight in ordered_buckets:
        target = int(limit * weight)
        weighted_targets[bucket] = min(target, total_per_bucket.get(bucket, 0))
        allocated += weighted_targets[bucket]

    # Distribute rounding remainder while respecting availability
    remainder = limit - allocated
    if remainder > 0:
        for bucket, _ in ordered_buckets:
            if remainder <= 0:
                break
            capacity = total_per_bucket.get(bucket, 0) - weighted_targets[bucket]
            if capacity <= 0:
                continue
            increment = min(capacity, remainder)
            weighted_targets[bucket] += increment
            remainder -= increment

    # If still short due to lack of supply, allow other buckets to fill the gap.
    if remainder > 0:
        for bucket, available in total_per_bucket.items():
            if remainder <= 0:
                break
            capacity = available - weighted_targets.get(bucket, 0)
            if capacity <= 0:
                continue
            increment = min(capacity, remainder)
            weighted_targets[bucket] = weighted_targets.get(bucket, 0) + increment
            remainder -= increment

    return weighted_targets


async def sample_posts_for_labeling(
    *,
    limit: int = 500,
    lookback_days: int = 30,
    min_communities: int = 20,
    random_seed: int | None = None,
    session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
) -> List[Dict[str, Any]]:
    """Select a diverse sample of posts for manual labeling."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    if min_communities <= 0:
        raise ValueError("min_communities must be positive")

    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    query = _build_query(since, limit)

    async with session_factory() as session:
        result = await session.execute(query)
        records = list(result.scalars())

    if len(records) < limit:
        raise ValueError(
            f"Only found {len(records)} posts in the last {lookback_days} days, "
            f"but {limit} samples are required."
        )

    rng = random.Random(random_seed)
    pool: List[Dict[str, Any]] = [_normalise_record(record) for record in records]
    rng.shuffle(pool)

    total_per_bucket: Dict[str, int] = Counter(item["_bucket"] for item in pool)
    targets = _derive_bucket_targets(limit=limit, total_per_bucket=total_per_bucket)
    available_total = sum(total_per_bucket.values())
    if available_total < limit:
        raise ValueError("Insufficient posts available to satisfy the sampling limit.")

    bucket_queues: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in pool:
        bucket_queues[item["_bucket"]].append(item)
    for items in bucket_queues.values():
        rng.shuffle(items)

    selected: List[Dict[str, Any]] = []
    used_ids: set[str] = set()
    community_counts: Counter[str] = Counter()
    bucket_counts: Counter[str] = Counter()

    # Phase 1: guarantee minimum community coverage
    for item in pool:
        if len(selected) >= limit or len(community_counts) >= min_communities:
            break
        subreddit = item["subreddit"]
        if not subreddit or subreddit in community_counts:
            continue
        post_id = item["post_id"]
        if post_id in used_ids:
            continue
        selected.append(item)
        used_ids.add(post_id)
        community_counts[subreddit] += 1
        bucket_counts[item["_bucket"]] += 1
        targets[item["_bucket"]] = max(0, targets[item["_bucket"]] - 1)

    # Phase 2: satisfy remaining bucket targets
    buckets_in_priority = sorted(
        _BUCKET_WEIGHTS.keys(),
        key=lambda name: _BUCKET_WEIGHTS[name],
        reverse=True,
    )
    while len(selected) < limit and any(targets[bucket] > 0 for bucket in targets):
        candidate_bucket = max(
            targets.items(),
            key=lambda kv: (kv[1], _BUCKET_WEIGHTS.get(kv[0], 0.0)),
        )[0]
        if targets[candidate_bucket] <= 0:
            break
        queue = bucket_queues.get(candidate_bucket, [])
        while queue:
            item = queue.pop()
            if item["post_id"] in used_ids:
                continue
            selected.append(item)
            used_ids.add(item["post_id"])
            community_counts[item["subreddit"]] += 1
            bucket_counts[item["_bucket"]] += 1
            targets[candidate_bucket] -= 1
            break
        else:
            targets[candidate_bucket] = 0

    # Phase 3: fill remaining slots with available posts, favouring higher scores
    if len(selected) < limit:
        remaining = [itm for itm in pool if itm["post_id"] not in used_ids]
        remaining.sort(
            key=lambda item: (
                _BUCKET_WEIGHTS[item["_bucket"]],
                item["score"],
                item["_created_at"],
            ),
            reverse=True,
        )
        for item in remaining:
            if len(selected) >= limit:
                break
            selected.append(item)
            used_ids.add(item["post_id"])
            community_counts[item["subreddit"]] += 1
            bucket_counts[item["_bucket"]] += 1

    selected = selected[:limit]
    if len(selected) < limit:
        raise RuntimeError(
            f"Sampling pipeline ended with {len(selected)} posts, "
            f"expected {limit}."
        )

    # Remove internal helper keys before returning.
    for item in selected:
        item.pop("_created_at", None)
        item.pop("_bucket", None)

    return selected


def export_samples_to_csv(
    samples: Sequence[Dict[str, Any]] | pd.DataFrame,
    output_path: Path,
) -> None:
    """Persist sampled posts to a CSV template for annotators."""
    if isinstance(samples, pd.DataFrame):
        df = samples.copy()
    else:
        df = pd.DataFrame(list(samples))

    for column in SAMPLE_COLUMNS:
        if column not in df:
            df[column] = ""

    df = df[SAMPLE_COLUMNS]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def load_labeled_data(csv_path: Path) -> pd.DataFrame:
    """Load the completed annotation CSV into a DataFrame."""
    df = pd.read_csv(csv_path)
    missing_columns = [col for col in SAMPLE_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Labeled CSV missing expected columns: {', '.join(missing_columns)}"
        )
    return df[SAMPLE_COLUMNS]

