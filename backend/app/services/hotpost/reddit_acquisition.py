from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RedditAcquisitionJob:
    query_part: str
    subreddit:Optional[ str]


@dataclass(frozen=True)
class RedditAcquisitionScope:
    jobs: tuple[RedditAcquisitionJob, ...]
    max_posts: int


@dataclass(frozen=True)
class RedditAcquisitionPlan:
    scout: RedditAcquisitionScope
    expand:Optional[ RedditAcquisitionScope]


def _build_jobs(
    *,
    query_parts: list[str],
    subreddits:Optional[ list[str]],
) -> tuple[RedditAcquisitionJob, ...]:
    active_queries = tuple(part for part in query_parts if part)
    if subreddits:
        return tuple(
            RedditAcquisitionJob(query_part=query_part, subreddit=subreddit)
            for query_part in active_queries
            for subreddit in subreddits
        )
    return tuple(
        RedditAcquisitionJob(query_part=query_part, subreddit=None)
        for query_part in active_queries
    )


def build_reddit_acquisition_plan(
    *,
    mode: str,
    query_parts: list[str],
    subreddits:Optional[ list[str]],
    limit: int,
    max_posts_per_search: int,
) -> RedditAcquisitionPlan:
    jobs = _build_jobs(query_parts=query_parts, subreddits=subreddits)
    if not jobs:
        raise ValueError("query_parts must contain at least one non-empty query")
    if len(jobs) == 1:
        return RedditAcquisitionPlan(
            scout=RedditAcquisitionScope(
                jobs=jobs,
                max_posts=max_posts_per_search,
            ),
            expand=None,
        )

    scout_job_count = 1 if subreddits is None else min(len(jobs), max(1, min(len(subreddits), 2)))
    scout_posts = min(max_posts_per_search, max(1, limit * 2))
    if mode == "rant" and subreddits:
        scout_job_count = min(len(jobs), max(1, min(len(subreddits), 2)))
        scout_posts = min(max_posts_per_search, max(1, limit * scout_job_count))
    scout = RedditAcquisitionScope(
        jobs=jobs[:scout_job_count],
        max_posts=scout_posts,
    )

    expand_jobs = jobs[scout_job_count:]
    if not expand_jobs and scout_posts < max_posts_per_search:
        expand_jobs = scout.jobs
    expand = (
        RedditAcquisitionScope(
            jobs=expand_jobs,
            max_posts=max_posts_per_search,
        )
        if expand_jobs
        else None
    )
    return RedditAcquisitionPlan(scout=scout, expand=expand)


def should_expand_acquisition(
    *,
    plan: RedditAcquisitionPlan,
    filtered_posts: int,
    limit: int,
) -> bool:
    return plan.expand is not None and filtered_posts < limit


def resolve_comment_post_limit(
    *,
    mode: str,
    evidence_count: int,
    max_comment_posts: int,
) -> int:
    """Resolve how many posts are allowed to enter comment fetching.

    rant 模式默认采用 voices-first，因此评论抓取要轻量且可控：
    - 低样本时只抓最前面的少量帖子
    - 高样本时也做硬上限，避免评论抓取拖垮整条链路
    """

    if mode != "rant":
        return max_comment_posts
    if evidence_count <= 6:
        return min(max_comment_posts, 2)
    if evidence_count <= 10:
        return min(max_comment_posts, 3)
    return min(max_comment_posts, 5)


__all__ = [
    "RedditAcquisitionJob",
    "RedditAcquisitionPlan",
    "RedditAcquisitionScope",
    "build_reddit_acquisition_plan",
    "resolve_comment_post_limit",
    "should_expand_acquisition",
]
