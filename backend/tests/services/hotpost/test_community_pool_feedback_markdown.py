from __future__ import annotations

from app.services.hotpost.community_pool_feedback_markdown import render_pool_feedback_markdown


def test_pool_feedback_markdown_renders_value_stage_and_score() -> None:
    rendered = render_pool_feedback_markdown(
        {
            "summary": {
                "input_rows": 1,
                "already_in_pool": 0,
                "promote_candidate": 0,
                "keep_testing": 1,
                "reject": 0,
            },
            "rows": [
                {
                    "community": "r/cursorai",
                    "source_scope": "ai-automation",
                    "topic_cluster": "workflow-friction",
                    "feedback_action": "keep_testing",
                    "value_assessment": {"stage": "validated", "score": 56},
                    "suggested_user_tags": ["AI工具与Agent"],
                    "evidence": {"total_evidence": 3},
                    "risks": ["duplicate_posts"],
                }
            ],
        }
    )

    assert "| Community | Scope | Topic Cluster | Action | Value Stage | Score |" in rendered
    assert "| r/cursorai | ai-automation | workflow-friction | keep_testing | validated | 56 |" in rendered
