from __future__ import annotations

from app.services.analysis.deduplicator import (
    DeduplicationStats,
    deduplicate_posts,
    get_last_stats,
)


def _make_post(idx: int, summary: str) -> dict[str, object]:
    return {
        "id": f"post-{idx}",
        "title": f"Example title {idx}",
        "summary": summary,
        "score": 10 + idx,
        "num_comments": idx,
        "subreddit": "r/test",
    }


def test_deduplication_stats_records_similarity_checks() -> None:
    posts = [
        _make_post(1, "Looking for automation workflows to speed reports."),
        _make_post(2, "Looking for automation workflow to speed report."),
        _make_post(3, "Automation workflows for faster reporting pipeline."),
    ]

    deduplicate_posts(posts)
    stats = get_last_stats()

    assert stats.total_posts == len(posts)
    assert stats.candidate_pairs > 0
    assert stats.similarity_checks > 0


def test_deduplication_stats_limits_fallback_on_large_sets() -> None:
    unique_posts = [
        _make_post(i, f"Unique content snippet {i} {i * 3}") for i in range(60)
    ]
    deduplicate_posts(unique_posts)
    stats_large = get_last_stats()
    assert stats_large.total_posts == len(unique_posts)
    assert stats_large.fallback_pairs == 0

    small_unique = [_make_post(i, f"Distinct fragment {i}") for i in range(5)]
    deduplicate_posts(small_unique)
    stats_small = get_last_stats()
    assert stats_small.fallback_pairs > 0
