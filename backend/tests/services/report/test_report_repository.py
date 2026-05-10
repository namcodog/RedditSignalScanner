from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.repositories.report_repository import ReportRepository


@pytest.mark.asyncio
async def test_persist_report_structured_repairs_missing_analysis_audit() -> None:
    db = SimpleNamespace(commit=AsyncMock())
    repository = ReportRepository(db)
    analysis = SimpleNamespace(
        sources={
            "report_tier": "A_full",
            "analysis_diagnostics": {
                "query_plan": {"intent": "open_topic"},
                "open_topic_route": {"warzone": "AI_Workflow"},
            },
        }
    )

    changed = await repository.persist_report_structured(
        analysis,
        {
            "pain_points": [
                {
                    "title": "任务和知识散落在多处",
                    "evidence_chain": [
                        {
                            "url": "https://www.reddit.com/r/ChatGPT/comments/demo/p1/",
                            "note": "pain",
                        }
                    ],
                }
            ],
            "opportunities": [
                {
                    "title": "团队协作进度与知识归档助手",
                    "evidence_chain": [
                        {
                            "url": "https://www.reddit.com/r/ClaudeAI/comments/demo/o1/",
                            "note": "opp",
                        }
                    ],
                }
            ],
        },
    )

    assert changed is True
    assert analysis.sources["analysis_audit"]["final_verdict"]["reason_code"] == "passed"
    db.commit.assert_awaited_once()
