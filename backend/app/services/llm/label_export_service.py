from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.llm.comment_label_export import (
    build_comment_activation_export as _build_comment_activation_export,
    export_comment_activation as _export_comment_activation,
    export_comments as _export_comments,
    export_comments_all as _export_comments_all,
)
from app.services.llm.label_export_io import (
    comment_payload_from_row as _comment_payload_from_row,
    interleave_selected_rows_by_domain as _interleave_selected_rows_by_domain,
    truncate_text as _truncate,
    write_jsonl as _write_jsonl,
)
from app.services.llm.post_label_export import (
    export_posts as _export_posts,
    export_posts_all as _export_posts_all,
)

DEFAULT_NOISE_RATIO = 0.1
DEFAULT_NOISE_MIN_SCORE = 20
DEFAULT_NOISE_MIN_COMMENTS = 10
DEFAULT_ACTIVATION_TARGET = 120_000
DEFAULT_ACTIVATION_BASE_QUOTA = 8_000
DEFAULT_ACTIVATION_FIRST_BATCH = 20_000
DEFAULT_ACTIVATION_BATCH_SIZE = 25_000


@dataclass(slots=True)
class LabelExportWorkflowInput:
    output_dir: Path
    post_limit: int
    comment_limit: int
    lookback_days: int
    export_all: bool
    include_noise: bool
    noise_ratio: float
    noise_min_score: int
    noise_min_comments: int
    top_comments: int
    posts_only: bool
    comments_only: bool
    historical_activation: bool
    activation_target: int
    activation_base_quota: int
    activation_first_batch_size: int
    activation_batch_size: int
    max_body_chars: int
    max_comment_chars: int


def run_label_export(workflow_input: LabelExportWorkflowInput) -> dict[str, Any]:
    if workflow_input.posts_only and workflow_input.comments_only:
        raise SystemExit("Choose only one of --posts-only or --comments-only.")
    if workflow_input.historical_activation and workflow_input.posts_only:
        raise SystemExit("--historical-activation only supports comments.")

    output_dir = workflow_input.output_dir
    post_limit = workflow_input.post_limit
    comment_limit = workflow_input.comment_limit
    if workflow_input.export_all and post_limit <= 0:
        post_limit = 0
    if workflow_input.export_all and comment_limit <= 0:
        comment_limit = 0

    posts_payload: list[dict[str, Any]] = []
    comments_payload: list[dict[str, Any]] = []
    activation_paths: list[str] = []

    if workflow_input.historical_activation:
        activation_batches, activation_summary = _export_comment_activation(
            lookback_days=workflow_input.lookback_days,
            max_body_chars=workflow_input.max_body_chars,
            target_total=workflow_input.activation_target,
            base_quota=workflow_input.activation_base_quota,
            first_batch_size=workflow_input.activation_first_batch_size,
            batch_size=workflow_input.activation_batch_size,
        )
        for idx, batch_rows in enumerate(activation_batches, start=1):
            path = output_dir / f"comments_activation_batch_{idx:03d}.jsonl"
            _write_jsonl(path, batch_rows)
            activation_paths.append(str(path))
        return {
            "status": "ok",
            "mode": "historical_activation",
            "comments": sum(len(batch) for batch in activation_batches),
            "comments_paths": activation_paths,
            **(activation_summary or {}),
        }

    if not workflow_input.comments_only:
        if workflow_input.export_all:
            posts_payload = _export_posts_all(
                limit=post_limit,
                lookback_days=workflow_input.lookback_days,
                max_body_chars=workflow_input.max_body_chars,
                max_comment_chars=workflow_input.max_comment_chars,
                top_comments=workflow_input.top_comments,
                include_noise=workflow_input.include_noise,
                noise_ratio=workflow_input.noise_ratio,
                noise_min_score=workflow_input.noise_min_score,
                noise_min_comments=workflow_input.noise_min_comments,
            )
        else:
            posts_payload = _export_posts(
                limit=post_limit,
                lookback_days=workflow_input.lookback_days,
                max_body_chars=workflow_input.max_body_chars,
                max_comment_chars=workflow_input.max_comment_chars,
                top_comments=workflow_input.top_comments,
            )

    if not workflow_input.posts_only:
        if workflow_input.export_all:
            comments_payload = _export_comments_all(
                limit=comment_limit,
                lookback_days=workflow_input.lookback_days,
                max_body_chars=workflow_input.max_body_chars,
                include_noise=workflow_input.include_noise,
                noise_ratio=workflow_input.noise_ratio,
                noise_min_score=workflow_input.noise_min_score,
            )
        else:
            comments_payload = _export_comments(
                limit=comment_limit,
                lookback_days=workflow_input.lookback_days,
                max_body_chars=workflow_input.max_body_chars,
            )

    posts_path = output_dir / "posts_batch_001.jsonl"
    comments_path = output_dir / "comments_batch_001.jsonl"
    if posts_payload:
        _write_jsonl(posts_path, posts_payload)
    if comments_payload:
        _write_jsonl(comments_path, comments_payload)

    return {
        "status": "ok",
        "mode": "default",
        "posts": len(posts_payload),
        "comments": len(comments_payload),
        "posts_path": str(posts_path) if posts_payload else None,
        "comments_path": str(comments_path) if comments_payload else None,
    }


__all__ = [
    "DEFAULT_ACTIVATION_BASE_QUOTA",
    "DEFAULT_ACTIVATION_BATCH_SIZE",
    "DEFAULT_ACTIVATION_FIRST_BATCH",
    "DEFAULT_ACTIVATION_TARGET",
    "DEFAULT_NOISE_MIN_COMMENTS",
    "DEFAULT_NOISE_MIN_SCORE",
    "DEFAULT_NOISE_RATIO",
    "LabelExportWorkflowInput",
    "_build_comment_activation_export",
    "_comment_payload_from_row",
    "_export_comment_activation",
    "_export_comments",
    "_export_comments_all",
    "_export_posts",
    "_export_posts_all",
    "_interleave_selected_rows_by_domain",
    "_truncate",
    "_write_jsonl",
    "run_label_export",
]
