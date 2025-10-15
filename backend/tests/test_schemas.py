from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
from uuid import uuid4

import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PACKAGE_ROOT = (PROJECT_ROOT / "backend").resolve()
if str(BACKEND_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_PACKAGE_ROOT))

from app.models.task import TaskStatus  # noqa: E402
from app.schemas.analysis import AnalysisRead  # noqa: E402
from app.schemas.task import TaskCreate, TaskRead  # noqa: E402


def test_task_create_validates_description_length() -> None:
    with pytest.raises(ValidationError):
        TaskCreate(product_description="too short")

    schema = TaskCreate(product_description="Build an AI note-taking assistant for researchers")
    assert schema.product_description.startswith("Build an AI")


def test_task_read_from_attributes() -> None:
    payload = TaskRead.model_validate(
        {
            "id": uuid4(),
            "user_id": uuid4(),
            "product_description": "Test product description long enough",
            "status": TaskStatus.PENDING,
            "error_message": None,
            "completed_at": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    assert payload.status is TaskStatus.PENDING


def test_analysis_schema_nested_validation() -> None:
    sample = AnalysisRead.model_validate(
        {
            "id": uuid4(),
            "task_id": uuid4(),
            "insights": {
                "pain_points": [
                    {
                        "description": "Integration complexity",
                        "frequency": 12,
                        "sentiment_score": -0.6,
                        "severity": "high",
                        "example_posts": [
                            {
                                "community": "r/saas",
                                "content": "Integration is slowing us down.",
                                "upvotes": 120,
                                "url": "https://reddit.com/r/saas/post-1",
                            }
                        ],
                        "user_examples": [
                            "Integration is slowing us down.",
                            "It takes weeks to stabilise new workflows.",
                        ],
                    }
                ],
                "competitors": [
                    {
                        "name": "CompetitorX",
                        "mentions": 34,
                        "sentiment": "mixed",
                        "strengths": ["Large community"],
                        "weaknesses": ["Slow updates"],
                        "market_share": 42.5,
                    }
                ],
                "opportunities": [
                    {
                        "description": "Realtime dashboards",
                        "relevance_score": 0.91,
                        "potential_users": "Product teams",
                        "key_insights": [
                            "Real-time visibility is missing",
                            "Teams want automated alerts",
                        ],
                    }
                ],
            },
            "sources": {
                "communities": ["r/productivity"],
                "posts_analyzed": 450,
                "cache_hit_rate": 0.78,
                "analysis_duration_seconds": 267,
                "reddit_api_calls": 32,
                "product_description": "AI assistant for operations teams",
                "communities_detail": [
                    {
                        "name": "r/productivity",
                        "categories": ["workflow", "operations"],
                        "mentions": 10,
                        "daily_posts": 200,
                        "avg_comment_length": 80,
                        "cache_hit_rate": 0.92,
                        "from_cache": True,
                    }
                ],
            },
            "confidence_score": Decimal("0.85"),
            "analysis_version": "1.0",
            "created_at": datetime.now(timezone.utc),
        }
    )

    assert sample.insights.pain_points[0].frequency == 12
    assert pytest.approx(sample.sources.cache_hit_rate, rel=1e-5) == 0.78
