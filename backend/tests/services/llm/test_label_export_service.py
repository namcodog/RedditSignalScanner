from __future__ import annotations

from pathlib import Path

from app.services.llm.label_export_service import (
    DEFAULT_ACTIVATION_BASE_QUOTA,
    DEFAULT_ACTIVATION_BATCH_SIZE,
    DEFAULT_ACTIVATION_FIRST_BATCH,
    DEFAULT_ACTIVATION_TARGET,
    DEFAULT_NOISE_MIN_COMMENTS,
    DEFAULT_NOISE_MIN_SCORE,
    DEFAULT_NOISE_RATIO,
    LabelExportWorkflowInput,
    run_label_export,
)


def _workflow_input(tmp_path: Path, **overrides: object) -> LabelExportWorkflowInput:
    params: dict[str, object] = {
        "output_dir": tmp_path,
        "post_limit": 10,
        "comment_limit": 20,
        "lookback_days": 30,
        "export_all": False,
        "include_noise": False,
        "noise_ratio": DEFAULT_NOISE_RATIO,
        "noise_min_score": DEFAULT_NOISE_MIN_SCORE,
        "noise_min_comments": DEFAULT_NOISE_MIN_COMMENTS,
        "top_comments": 3,
        "posts_only": False,
        "comments_only": False,
        "historical_activation": False,
        "activation_target": DEFAULT_ACTIVATION_TARGET,
        "activation_base_quota": DEFAULT_ACTIVATION_BASE_QUOTA,
        "activation_first_batch_size": DEFAULT_ACTIVATION_FIRST_BATCH,
        "activation_batch_size": DEFAULT_ACTIVATION_BATCH_SIZE,
        "max_body_chars": 120,
        "max_comment_chars": 80,
    }
    params.update(overrides)
    return LabelExportWorkflowInput(**params)


def test_run_label_export_default_mode_writes_posts_and_comments(
    monkeypatch,
    tmp_path: Path,
) -> None:
    writes: list[tuple[Path, list[dict[str, object]]]] = []

    monkeypatch.setattr(
        "app.services.llm.label_export_service._export_posts",
        lambda **_: [{"id": 1, "task_type": "post_label"}],
    )
    monkeypatch.setattr(
        "app.services.llm.label_export_service._export_comments",
        lambda **_: [{"id": 2, "task_type": "comment_label"}],
    )
    monkeypatch.setattr(
        "app.services.llm.label_export_service._write_jsonl",
        lambda path, rows: writes.append((path, rows)),
    )

    result = run_label_export(_workflow_input(tmp_path))

    assert result["mode"] == "default"
    assert result["posts"] == 1
    assert result["comments"] == 1
    assert [path.name for path, _rows in writes] == [
        "posts_batch_001.jsonl",
        "comments_batch_001.jsonl",
    ]


def test_run_label_export_historical_activation_writes_batches(
    monkeypatch,
    tmp_path: Path,
) -> None:
    writes: list[tuple[Path, list[dict[str, object]]]] = []

    monkeypatch.setattr(
        "app.services.llm.label_export_service._export_comment_activation",
        lambda **_: (
            [
                [{"id": 11, "task_type": "comment_label"}],
                [{"id": 12, "task_type": "comment_label"}],
            ],
            {"eligible_comment_pool": 2},
        ),
    )
    monkeypatch.setattr(
        "app.services.llm.label_export_service._write_jsonl",
        lambda path, rows: writes.append((path, rows)),
    )

    result = run_label_export(
        _workflow_input(
            tmp_path,
            historical_activation=True,
            comments_only=True,
        )
    )

    assert result["mode"] == "historical_activation"
    assert result["comments"] == 2
    assert result["eligible_comment_pool"] == 2
    assert [path.name for path, _rows in writes] == [
        "comments_activation_batch_001.jsonl",
        "comments_activation_batch_002.jsonl",
    ]
