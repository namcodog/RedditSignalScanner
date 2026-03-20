from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.services.llm import label_import_workflow as workflow_mod
from app.services.llm.label_import_workflow import (
    LabelImportWorkflowInput,
    import_comment_label_rows,
    import_label_files,
)


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False


@pytest.mark.asyncio
async def test_import_comment_label_rows_delegates_to_shared_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = _FakeSession()
    built_rows: list[dict[str, Any]] = []
    persisted_rows: list[dict[str, Any]] = []
    normalized_payloads: list[dict[str, Any]] = []
    scored_payloads: list[dict[str, Any]] = []

    monkeypatch.setattr(
        workflow_mod,
        "SessionFactory",
        lambda: _FakeSessionContext(fake_session),
    )

    def _fake_normalize_comment_analysis(item: dict[str, Any]) -> dict[str, Any]:
        normalized = {"main_intent": str(item.get("main_intent") or "offtopic").lower()}
        normalized_payloads.append(normalized)
        return normalized

    def _fake_score_comment(analysis: dict[str, Any]) -> Any:
        class _Score:
            value_score = 5.5
            opportunity_score = 0.3
            business_pool = "lab"

        scored_payloads.append(analysis)
        return _Score()

    def _fake_build_comment_label_row(**kwargs: Any) -> dict[str, Any]:
        row = {
            "comment_id": kwargs["comment_id"],
            "business_pool": kwargs["score"]["business_pool"],
        }
        built_rows.append(row)
        return row

    async def _fake_upsert_comment_label_rows(
        *,
        session: Any,
        rows: list[dict[str, Any]],
    ) -> int:
        assert session is fake_session
        persisted_rows.extend(rows)
        return len(rows)

    monkeypatch.setattr(
        workflow_mod,
        "normalize_comment_analysis",
        _fake_normalize_comment_analysis,
    )
    monkeypatch.setattr(workflow_mod, "score_comment_analysis", _fake_score_comment)
    monkeypatch.setattr(
        workflow_mod,
        "build_comment_label_row",
        _fake_build_comment_label_row,
    )
    monkeypatch.setattr(
        workflow_mod,
        "upsert_comment_label_rows",
        _fake_upsert_comment_label_rows,
    )

    imported = await import_comment_label_rows(
        items=[
            {
                "id": 101,
                "sentiment": 0.1,
                "purchase_intent_score": 0.2,
                "pain_tags": ["price"],
                "aspect_tags": ["cost"],
                "main_intent": "complain",
                "entities": {"known": ["roborock"], "new": []},
            }
        ],
        llm_version="v-test",
        model_name="codex-test",
        prompt_version="p1",
    )

    assert imported == 1
    assert fake_session.commits == 1
    assert normalized_payloads == [{"main_intent": "complain"}]
    assert scored_payloads == normalized_payloads
    assert built_rows == [{"comment_id": 101, "business_pool": "lab"}]
    assert persisted_rows == built_rows


@pytest.mark.asyncio
async def test_import_label_files_reports_progress(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    comments_path = tmp_path / "comments.jsonl"
    comments_path.write_text('{"id": 1}\n{"id": 2}\n', encoding="utf-8")
    posts_path = tmp_path / "posts.jsonl"
    posts_path.write_text('{"id": 11}\n', encoding="utf-8")

    progress: list[tuple[str, int, int]] = []

    async def _fake_import_posts(**kwargs: Any) -> int:
        return len(kwargs["items"])

    async def _fake_import_comments(**kwargs: Any) -> int:
        return len(kwargs["items"])

    monkeypatch.setattr(workflow_mod, "import_post_label_rows", _fake_import_posts)
    monkeypatch.setattr(
        workflow_mod,
        "import_comment_label_rows",
        _fake_import_comments,
    )

    result = await import_label_files(
        workflow_input=LabelImportWorkflowInput(
            posts_path=posts_path,
            comments_path=comments_path,
            batch_size=1,
            llm_version="v1",
            model_name="gpt-test",
            prompt_version="p1",
        ),
        progress_callback=lambda kind, imported, total: progress.append(
            (kind, imported, total)
        ),
    )

    assert result.posts_total == 1
    assert result.posts_imported == 1
    assert result.comments_total == 2
    assert result.comments_imported == 2
    assert progress == [
        ("posts", 1, 1),
        ("comments", 1, 2),
        ("comments", 2, 2),
    ]
