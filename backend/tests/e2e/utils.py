from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict

import jwt
from httpx import AsyncClient

from app.core.config import get_settings
from app.services.analysis_engine import AnalysisResult
from app.tasks import analysis_task


SampleInsights = {
    "pain_points": [
        {"description": "Reddit users struggle to track feature requests", "frequency": 42, "sentiment_score": -0.62},
        {"description": "Manual synthesis of feedback is slow", "frequency": 35, "sentiment_score": -0.55},
        {"description": "Teams lack a single source of truth for user pain", "frequency": 33, "sentiment_score": -0.48},
        {"description": "Hard to quantify community demand", "frequency": 28, "sentiment_score": -0.41},
        {"description": "Competitive landscape evolves faster than research cadence", "frequency": 21, "sentiment_score": -0.37},
    ],
    "competitors": [
        {"name": "Notion AI", "mentions": 18, "sentiment": "mixed"},
        {"name": "Coda", "mentions": 14, "sentiment": "neutral"},
        {"name": "Productboard", "mentions": 12, "sentiment": "negative"},
    ],
    "opportunities": [
        {"description": "Automate signal detection for emerging Reddit threads", "confidence": 0.82},
        {"description": "Surface community benchmarks to prioritise roadmap", "confidence": 0.78},
        {"description": "Provide proactive alerts for fast-growing subreddits", "confidence": 0.74},
    ],
}

SampleCommunities = [
    {"name": "r/startups", "mentions": 32, "cache_hit_rate": 0.95, "categories": ["startup"], "daily_posts": 185, "avg_comment_length": 72, "from_cache": True},
    {"name": "r/ProductManagement", "mentions": 24, "cache_hit_rate": 0.92, "categories": ["product"], "daily_posts": 96, "avg_comment_length": 85, "from_cache": True},
    {"name": "r/technology", "mentions": 20, "cache_hit_rate": 0.88, "categories": ["tech"], "daily_posts": 320, "avg_comment_length": 42, "from_cache": False},
]


def install_fast_analysis(monkeypatch, *, cache_stats: Dict[str, int] | None = None) -> None:
    """
    Replace the heavy analysis pipeline with a deterministic stub so end-to-end tests
    can execute quickly while still validating the PRD contract.
    """

    async def fast_run_analysis(summary) -> AnalysisResult:  # pragma: no cover - exercised via e2e tests
        if cache_stats is not None:
            cache_stats.setdefault("total", 0)
            cache_stats.setdefault("hits", 0)
            cache_stats["total"] += 1
            # Simulate 95% cache hit rate
            if cache_stats["total"] % 20 != 0:
                cache_stats["hits"] += 1
        return AnalysisResult(
            insights=SampleInsights,
            sources={
                "communities": [c["name"] for c in SampleCommunities],
                "communities_detail": SampleCommunities,
                "posts_analyzed": 64,
                "cache_hit_rate": 0.95,
                "analysis_duration_seconds": 1.3,
            },
            report_html="<h1>Reddit Signal Scanner Report</h1>",
            action_items=SampleInsights.get("action_items", []),
        )

    monkeypatch.setattr(analysis_task, "run_analysis", fast_run_analysis)


async def wait_for_task_completion(
    client: AsyncClient,
    token: str,
    task_id: str,
    *,
    timeout: float = 15.0,
    poll_interval: float = 0.1,
    expected_status: str = "completed",
) -> Dict[str, Any]:
    """Poll the status endpoint until the given task is completed or the timeout elapses."""

    deadline = time.perf_counter() + timeout
    headers = {"Authorization": f"Bearer {token}"}
    last_payload: Dict[str, Any] = {}

    while time.perf_counter() < deadline:
        response = await client.get(f"/api/status/{task_id}", headers=headers)
        if response.status_code == 200:
            payload = response.json()
            last_payload = payload
            if payload["status"] == expected_status:
                return payload
            if expected_status == "completed" and payload["status"] in {"pending", "processing"}:
                report_response = await client.get(f"/api/report/{task_id}", headers=headers)
                if report_response.status_code == 200:
                    payload["status"] = "completed"
                    return payload
        await asyncio.sleep(poll_interval)

    raise TimeoutError(
        f"Task {task_id} did not reach status '{expected_status}' within {timeout} seconds; "
        f"last payload: {last_payload}"
    )


def issue_expired_token(user_id: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": f"expired+{user_id}@example.com",
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) - 60,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
