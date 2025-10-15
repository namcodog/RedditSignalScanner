from __future__ import annotations

"""
Deterministic test data generators for backend tests (Day14).

These helpers avoid DB dependencies by returning Pydantic schema payloads
or lightweight dataclasses used across the codebase.
"""

import random
import string
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID, uuid4

from app.models.task import TaskStatus
from app.schemas.task import TaskSummary
from app.services.reddit_client import RedditPost


def seed_rng(seed: int = 42) -> None:
    random.seed(seed)


def random_text(prefix: str, n: int = 12) -> str:
    letters = string.ascii_lowercase
    return f"{prefix}-" + "".join(random.choice(letters) for _ in range(max(1, n)))


def make_task_summary(description: str | None = None, *, status: TaskStatus = TaskStatus.PENDING) -> TaskSummary:
    now = datetime.now(timezone.utc)
    desc = description or "AI-powered note taking app for researchers needing nightly summaries."
    return TaskSummary(
        id=uuid4(),
        status=status,
        product_description=desc,
        created_at=now,
        updated_at=now,
    )


def make_reddit_posts(subreddit: str, *, count: int = 5) -> List[RedditPost]:
    posts: List[RedditPost] = []
    for i in range(count):
        posts.append(
            RedditPost(
                id=f"{subreddit}-{i}",
                title=f"{random_text('Title', 8)} {i}",
                selftext=f"{random_text('Content', 24)}",
                score=100 + i,
                num_comments=10 + i,
                created_utc=float(i + 0.1),
                subreddit=subreddit,
                author="tester",
                url=f"https://reddit.com/{subreddit}/{i}",
                permalink=f"/{subreddit}/{i}",
            )
        )
    return posts


def make_example_post_dict(subreddit: str, content: str, *, upvotes: int = 120) -> Dict[str, Any]:
    return {
        "community": subreddit,
        "content": content,
        "upvotes": upvotes,
        "url": f"https://reddit.com/{subreddit}/x",
        "author": "tester",
        "permalink": f"/{subreddit}/x",
    }


def make_analysis_insights(min_items: int = 3) -> Dict[str, Any]:
    pains: List[Dict[str, Any]] = []
    comps: List[Dict[str, Any]] = []
    opps: List[Dict[str, Any]] = []

    for i in range(min_items):
        pains.append(
            {
                "description": f"Pain-{i}",
                "frequency": 1 + i,
                "sentiment_score": -0.2 * (i + 1),
                "severity": "high" if i % 3 == 0 else ("medium" if i % 3 == 1 else "low"),
                "example_posts": [make_example_post_dict("r/startups", f"Example {i}")],
                "user_examples": [f"Quote {i}a", f"Quote {i}b", f"Quote {i}c"],
            }
        )

        comps.append(
            {
                "name": f"Competitor-{i}",
                "mentions": 10 + i,
                "sentiment": "mixed",
                "strengths": ["Strong community"],
                "weaknesses": ["Needs polish"],
                "market_share": 5 + i,
            }
        )

        opps.append(
            {
                "description": f"Opportunity-{i}",
                "relevance_score": 0.5 + (i * 0.05),
                "potential_users": f"约{100 + i}个潜在团队",
                "key_insights": [f"Insight {i}a", f"Insight {i}b", f"Insight {i}c", f"Insight {i}d"],
            }
        )

    return {"pain_points": pains, "competitors": comps, "opportunities": opps}


__all__ = [
    "seed_rng",
    "random_text",
    "make_task_summary",
    "make_reddit_posts",
    "make_example_post_dict",
    "make_analysis_insights",
]

