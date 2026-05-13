from __future__ import annotations

import pytest

from app.tasks import scoring_task


def test_score_new_posts_v1_returns_explicit_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run(coro):
        coro.close()
        return {"processed": 3}

    monkeypatch.setattr(scoring_task, "run_coro", _fake_run)

    result = scoring_task.score_new_posts_v1(limit=3)

    assert result["status"] == "completed"
    assert result["task_scope"] == "default_score_backfill"
    assert result["score_source"] == "rulebook_v1_default_fill"
    assert result["score_target"] == "posts"
    assert result["degraded_reasons"] == []
    assert result["processed"] == 3


def test_score_new_comments_v1_returns_explicit_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run(coro):
        coro.close()
        return {"processed": 2}

    monkeypatch.setattr(scoring_task, "run_coro", _fake_run)

    result = scoring_task.score_new_comments_v1(limit=2)

    assert result["status"] == "completed"
    assert result["task_scope"] == "default_score_backfill"
    assert result["score_source"] == "rulebook_v1_default_fill"
    assert result["score_target"] == "comments"
    assert result["degraded_reasons"] == []
    assert result["processed"] == 2
