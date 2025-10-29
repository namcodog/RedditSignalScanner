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
        {
            "description": "Reddit users struggle to track feature requests",
            "frequency": 12,
            "sentiment_score": -0.42,
            "severity": "high",
            "example_posts": [],
            "user_examples": [],
        },
        {
            "description": "Manual synthesis of feedback is slow",
            "frequency": 10,
            "sentiment_score": -0.35,
            "severity": "medium",
            "example_posts": [],
            "user_examples": [],
        },
        {
            "description": "Teams lack a single source of truth for user pain",
            "frequency": 9,
            "sentiment_score": 0.15,
            "severity": "medium",
            "example_posts": [],
            "user_examples": [],
        },
        {
            "description": "Hard to quantify community demand",
            "frequency": 8,
            "sentiment_score": 0.05,
            "severity": "low",
            "example_posts": [],
            "user_examples": [],
        },
        {
            "description": "Competitive landscape evolves faster than research cadence",
            "frequency": 7,
            "sentiment_score": 0.02,
            "severity": "low",
            "example_posts": [],
            "user_examples": [],
        },
    ],
    "competitors": [
        {
            "name": "Notion AI",
            "mentions": 5,
            "sentiment": "positive",
            "strengths": ["Seamless docs integration"],
            "weaknesses": ["Limited Reddit ingestion"],
            "market_share": 12.5,
        },
        {
            "name": "Coda",
            "mentions": 4,
            "sentiment": "neutral",
            "strengths": ["Flexible workflows"],
            "weaknesses": ["Manual insights tagging"],
            "market_share": 8.3,
        },
        {
            "name": "Productboard",
            "mentions": 3,
            "sentiment": "negative",
            "strengths": ["Roadmap alignment"],
            "weaknesses": ["Slow Reddit coverage"],
            "market_share": 9.1,
        },
    ],
    "opportunities": [
        {
            "description": "Automate signal detection for emerging Reddit threads",
            "relevance_score": 0.9,
            "potential_users": "Growth and research teams tracking early demand signals",
            "key_insights": ["High volume of new product talk in r/startups"],
        },
        {
            "description": "Surface community benchmarks to prioritise roadmap",
            "relevance_score": 0.82,
            "potential_users": "Product managers planning quarterly priorities",
            "key_insights": ["Clear gaps across go-to-market communities"],
        },
        {
            "description": "Provide proactive alerts for fast-growing subreddits",
            "relevance_score": 0.78,
            "potential_users": "Marketing teams monitoring sudden surges",
            "key_insights": ["Emerging mentions across r/technology and r/AI"],
        },
    ],
    "action_items": [
        {
            "problem_definition": "Founders cannot keep up with Reddit feedback velocity",
            "evidence_chain": [
                {
                    "title": "Weekly founder pain",
                    "url": "https://reddit.com/r/startups",
                    "note": "High-frequency posts requesting synthesis tools",
                }
            ],
            "suggested_actions": [
                "Ship automated Reddit digests for founder cohorts",
                "Highlight biggest opportunity gaps in pitch decks",
            ],
            "confidence": 0.9,
            "urgency": 0.8,
            "product_fit": 0.85,
            "priority": 0.88,
        }
    ],
    "entity_summary": {
        "brands": [
            {"name": "Notion AI", "mentions": 3},
            {"name": "Coda", "mentions": 2},
        ],
        "features": [
            {"name": "automation", "mentions": 4},
            {"name": "workflow", "mentions": 3},
        ],
        "pain_points": [
            {"name": "slow", "mentions": 2},
        ],
    },
}

SampleCommunities = [
    {
        "name": "r/startups",
        "mentions": 32,
        "cache_hit_rate": 0.95,
        "categories": ["startup"],
        "daily_posts": 185,
        "avg_comment_length": 72,
        "from_cache": True,
    },
    {
        "name": "r/ProductManagement",
        "mentions": 24,
        "cache_hit_rate": 0.92,
        "categories": ["product"],
        "daily_posts": 96,
        "avg_comment_length": 85,
        "from_cache": True,
    },
    {
        "name": "r/technology",
        "mentions": 20,
        "cache_hit_rate": 0.88,
        "categories": ["tech"],
        "daily_posts": 320,
        "avg_comment_length": 42,
        "from_cache": False,
    },
]


def install_fast_analysis(
    monkeypatch, *, cache_stats: Dict[str, int] | None = None
) -> None:
    """
    Replace the heavy analysis pipeline with a deterministic stub so end-to-end tests
    can execute quickly while still validating the PRD contract.
    """

    async def fast_run_analysis(
        summary,
    ) -> AnalysisResult:  # pragma: no cover - exercised via e2e tests
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
                "analysis_duration_seconds": 1,
            },
            report_html="<h1>Reddit Signal Scanner Report</h1>",
            action_items=SampleInsights.get("action_items", []),
            confidence_score=0.95,  # 高置信度（基于 95% 缓存命中率和充足的数据量）
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
            # 如果任务失败，立即抛出 TimeoutError 让调用端按失败路径断言（更稳定，避免跨测试的状态干扰）
            if payload["status"] == "failed":
                raise TimeoutError(
                    f"Task {task_id} failed before reaching status '{expected_status}'; last payload: {payload}"
                )
            if expected_status == "completed" and payload["status"] in {
                "pending",
                "processing",
            }:
                report_response = await client.get(
                    f"/api/report/{task_id}", headers=headers
                )
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
