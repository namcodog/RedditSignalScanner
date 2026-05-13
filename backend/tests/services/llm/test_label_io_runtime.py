from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.llm import label_io_runtime as runtime


def test_run_label_export_cli_builds_workflow_input(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def _fake_run_label_export(workflow_input):  # type: ignore[no-untyped-def]
        captured["workflow_input"] = workflow_input
        return {"status": "ok", "posts": 1, "comments": 2}

    monkeypatch.setattr(runtime, "run_label_export", _fake_run_label_export)

    settings = SimpleNamespace(
        llm_label_body_chars=777,
        llm_label_comment_chars=333,
    )

    result = runtime.run_label_export_cli(
        settings=settings,
        cli_input=runtime.LabelExportCliInput(
            output_dir=tmp_path,
            post_limit=10,
            comment_limit=20,
            lookback_days=30,
            export_all=True,
            include_noise=False,
            noise_ratio=0.1,
            noise_min_score=20,
            noise_min_comments=10,
            top_comments=2,
            posts_only=False,
            comments_only=False,
            historical_activation=False,
            activation_target=100,
            activation_base_quota=20,
            activation_first_batch_size=50,
            activation_batch_size=25,
        ),
    )

    assert result == {"status": "ok", "posts": 1, "comments": 2}
    workflow_input = captured["workflow_input"]
    assert workflow_input.output_dir == tmp_path
    assert workflow_input.post_limit == 10
    assert workflow_input.comment_limit == 20
    assert workflow_input.max_body_chars == 777
    assert workflow_input.max_comment_chars == 333


@pytest.mark.asyncio
async def test_run_label_import_cli_guards_gold_and_reports_progress(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    posts_path = tmp_path / "posts.jsonl"
    posts_path.write_text('{"id":1}\n', encoding="utf-8")
    printed: list[str] = []

    async def _fake_import_label_files(*, workflow_input, progress_callback):  # type: ignore[no-untyped-def]
        progress_callback("posts", 1, 1)
        return SimpleNamespace(posts_total=1, posts_imported=1, comments_total=0, comments_imported=0)

    monkeypatch.setattr(runtime, "import_label_files", _fake_import_label_files)

    with pytest.raises(SystemExit):
        await runtime.run_label_import_cli(
            cli_input=runtime.LabelImportCliInput(
                posts_path=posts_path,
                comments_path=None,
                batch_size=100,
                llm_version="v1",
                model_name="model-x",
                prompt_version="p1",
                database_url="postgresql+asyncpg://x/reddit_signal_scanner",
                allow_gold=False,
            ),
            progress_writer=printed.append,
        )

    result = await runtime.run_label_import_cli(
        cli_input=runtime.LabelImportCliInput(
            posts_path=posts_path,
            comments_path=None,
            batch_size=100,
            llm_version="v1",
            model_name="model-x",
            prompt_version="p1",
            database_url="postgresql+asyncpg://x/reddit_signal_scanner_dev",
            allow_gold=False,
        ),
        progress_writer=printed.append,
    )

    assert result.posts_total == 1
    assert printed == ["[posts] imported 1/1"]
