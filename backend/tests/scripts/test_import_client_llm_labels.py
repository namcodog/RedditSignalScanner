from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import_mod = importlib.import_module("scripts.import.import_client_llm_labels")


@pytest.mark.asyncio
async def test_import_labels_delegates_to_workflow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    comments_path = tmp_path / "comments.jsonl"
    comments_path.write_text('{"id": 1}\n', encoding="utf-8")
    posts_path = tmp_path / "posts.jsonl"
    posts_path.write_text('{"id": 2}\n', encoding="utf-8")
    progress: list[str] = []

    async def _fake_run_label_import_cli(*, cli_input, progress_writer):  # type: ignore[no-untyped-def]
        assert cli_input.posts_path == posts_path
        assert cli_input.comments_path == comments_path
        assert cli_input.batch_size == 123
        assert cli_input.llm_version == "v-test"
        assert cli_input.model_name == "model-x"
        assert cli_input.prompt_version == "p-test"
        progress_writer("[posts] imported 1/1")
        progress_writer("[comments] imported 1/1")
        return None

    monkeypatch.setattr(import_mod, "run_label_import_cli", _fake_run_label_import_cli)
    monkeypatch.setattr(
        "builtins.print",
        lambda message: progress.append(str(message)),
    )

    await import_mod._import_labels(
        posts_path=posts_path,
        comments_path=comments_path,
        batch_size=123,
        llm_version="v-test",
        model_name="model-x",
        prompt_version="p-test",
    )

    assert progress == [
        "[posts] imported 1/1",
        "[comments] imported 1/1",
    ]
