from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.report import Report
from app.models.task import Task, TaskStatus
from app.models.user import MembershipLevel, User
from app.services.analysis.analysis_engine import AnalysisResult


pytestmark = pytest.mark.asyncio


async def test_golden_business_flow_persists_task_analysis_and_report(
    client: AsyncClient,
    token_factory,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Hard-disable any LLM/network enhancements for deterministic & offline-safe tests.
    from app.core import config as config_module

    monkeypatch.setattr(config_module.settings, "enable_llm_summary", False)
    monkeypatch.setattr(config_module.settings, "llm_model_name", "local-extractive")
    monkeypatch.setattr(config_module.settings, "report_quality_level", "basic")

    token, user_id = await token_factory()
    headers = {"Authorization": f"Bearer {token}"}

    # Report access is PRO+ only; upgrade the freshly created user in-place for this test.
    user = await db_session.get(User, uuid.UUID(user_id))
    assert user is not None
    user.membership_level = MembershipLevel.PRO
    await db_session.commit()

    from app.api.v1.endpoints import analyze as analyze_endpoint
    from app.tasks import analysis_task as analysis_task_module

    async def stub_run_analysis(_summary) -> AnalysisResult:
        return AnalysisResult(
            insights={
                "pain_points": [
                    {
                        "description": "Onboarding takes too long and users drop off.",
                        "frequency": 42,
                        "sentiment_score": -0.3,
                        "severity": "high",
                        "example_posts": [
                            {
                                "community": "r/startups",
                                "content": "Our onboarding is confusing; users churn before activation.",
                                "upvotes": 123,
                                "url": "https://www.reddit.com/r/startups/comments/abc123/test/",
                                "author": "test_user",
                                "permalink": "/r/startups/comments/abc123/test/",
                                "duplicate_ids": [],
                                "evidence_count": 1,
                            }
                        ],
                        "user_examples": ["Onboarding feels like homework."],
                    }
                ],
                "competitors": [
                    {
                        "name": "CompetitorX",
                        "mentions": 10,
                        "sentiment": "mixed",
                        "strengths": ["Fast setup"],
                        "weaknesses": ["Expensive"],
                        "market_share": 12.5,
                        "context_snippets": ["CompetitorX is okay but pricey."],
                        "layer": "summary",
                    }
                ],
                "opportunities": [
                    {
                        "description": "Simplify onboarding to reduce time-to-value.",
                        "relevance_score": 0.85,
                        "potential_users": "Early-stage SaaS founders",
                        "potential_users_est": 5000,
                        "linked_pain_cluster": "Onboarding friction",
                        "top_channels": ["r/startups"],
                        "key_insights": ["Users want faster time-to-value."],
                        "source_examples": [],
                    }
                ],
            },
            sources={
                "communities": ["r/startups"],
                "posts_analyzed": 100,
                "cache_hit_rate": 0.95,
                "analysis_duration_seconds": 1,
                "reddit_api_calls": 0,
                "data_source": "synthetic",
            },
            report_html="<html><body>stub report</body></html>",
            action_items=[
                {
                    "problem_definition": "Reduce onboarding friction",
                    "evidence_chain": [],
                    "suggested_actions": ["Shorten onboarding steps"],
                    "confidence": 0.9,
                    "urgency": 0.7,
                    "product_fit": 0.8,
                    "priority": 0.85,
                    "communities": ["r/startups"],
                }
            ],
            confidence_score=0.9,
        )

    async def force_inline_schedule(
        task_id: uuid.UUID, user_id: uuid.UUID, _settings
    ) -> None:
        await analysis_task_module.execute_analysis_pipeline(task_id, user_id=user_id)

    monkeypatch.setattr(analysis_task_module, "run_analysis", stub_run_analysis)
    monkeypatch.setattr(analyze_endpoint, "_schedule_analysis", force_inline_schedule)

    resp = await client.post(
        "/api/analyze",
        headers=headers,
        json={"product_description": "Test product description for golden flow."},
    )
    assert resp.status_code == 201
    task_id = uuid.UUID(resp.json()["task_id"])

    # DB: task/analysis/report must exist and be completed
    task = await db_session.get(Task, task_id)
    assert task is not None
    assert task.user_id == uuid.UUID(user_id)
    assert task.status == TaskStatus.COMPLETED

    analysis = (
        await db_session.execute(select(Analysis).where(Analysis.task_id == task_id))
    ).scalar_one()
    assert analysis.sources["posts_analyzed"] == 100
    assert analysis.sources["cache_hit_rate"] == 0.95
    assert analysis.sources["communities_count"] == 1
    assert analysis.sources["comments_analyzed"] == 0
    crawler_hash = analysis.sources.get("crawler_config_sha256")
    assert isinstance(crawler_hash, str)
    assert len(crawler_hash) == 64

    report = (
        await db_session.execute(select(Report).where(Report.analysis_id == analysis.id))
    ).scalar_one()
    assert "stub report" in report.html_content

    # API: status/report should be retrievable end-to-end
    status_resp = await client.get(f"/api/status/{task_id}", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == TaskStatus.COMPLETED.value

    report_resp = await client.get(f"/api/report/{task_id}", headers=headers)
    assert report_resp.status_code == 200
    body = report_resp.json()
    assert body["task_id"] == str(task_id)
    assert body["status"] == TaskStatus.COMPLETED.value
    assert body["report_html"].startswith("<")
