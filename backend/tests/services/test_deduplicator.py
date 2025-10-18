from __future__ import annotations

from typing import List

from app.services.analysis.deduplicator import deduplicate_posts


def _make_post(post_id: str, title: str, summary: str) -> dict:
    return {
        "id": post_id,
        "title": title,
        "summary": summary,
        "score": 50,
        "num_comments": 4,
        "subreddit": "r/startups",
        "author": "tester",
        "url": f"https://reddit.com/r/startups/{post_id}",
        "permalink": f"/r/startups/{post_id}",
    }


def test_deduplicate_posts_clusters_similar_text() -> None:
    posts: List[dict] = [
        _make_post(
            "primary-1",
            "Need AI automation assistant for weekly reports",
            "Looking for an AI automation assistant that can summarise weekly reports for stakeholders.",
        ),
        _make_post(
            "duplicate-1",
            "Need automation assistant for weekly report summaries",
            "Looking for automation assistant that summarises the weekly stakeholder reports with AI.",
        ),
        _make_post(
            "unique-1",
            "Manual workflows are too slow for our research ops",
            "Research ops complain about slow manual workflows and poor tooling.",
        ),
    ]

    deduped = deduplicate_posts(posts, threshold=0.82)

    assert len(deduped) == 2
    primary = next(post for post in deduped if post["id"] == "primary-1")
    assert primary["evidence_count"] == 2
    assert "duplicate-1" in primary["duplicate_ids"]
    assert all(id_ != "duplicate-1" for id_ in primary["duplicate_ids"] if id_ == "primary-1")
    unique = next(post for post in deduped if post["id"] == "unique-1")
    assert unique["evidence_count"] == 1
    assert unique["duplicate_ids"] == []
