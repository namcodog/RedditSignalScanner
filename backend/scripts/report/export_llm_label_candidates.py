from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import get_settings
from app.services.llm.label_export_service import (
    DEFAULT_ACTIVATION_BASE_QUOTA,
    DEFAULT_ACTIVATION_BATCH_SIZE,
    DEFAULT_ACTIVATION_FIRST_BATCH,
    DEFAULT_ACTIVATION_TARGET,
    DEFAULT_NOISE_MIN_COMMENTS,
    DEFAULT_NOISE_MIN_SCORE,
    DEFAULT_NOISE_RATIO,
)
from app.services.llm.label_io_runtime import LabelExportCliInput, run_label_export_cli


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Export LLM label candidates.")
    parser.add_argument("--output-dir", default="reports/llm-client")
    parser.add_argument("--post-limit", type=int, default=settings.llm_label_post_limit)
    parser.add_argument("--comment-limit", type=int, default=settings.llm_label_comment_limit)
    parser.add_argument("--lookback-days", type=int, default=settings.llm_label_lookback_days)
    parser.add_argument("--export-all", action="store_true")
    parser.add_argument("--include-noise", action="store_true")
    parser.add_argument("--noise-ratio", type=float, default=DEFAULT_NOISE_RATIO)
    parser.add_argument("--noise-min-score", type=int, default=DEFAULT_NOISE_MIN_SCORE)
    parser.add_argument("--noise-min-comments", type=int, default=DEFAULT_NOISE_MIN_COMMENTS)
    parser.add_argument("--top-comments", type=int, default=2)
    parser.add_argument("--posts-only", action="store_true")
    parser.add_argument("--comments-only", action="store_true")
    parser.add_argument("--historical-activation", action="store_true")
    parser.add_argument("--activation-target", type=int, default=DEFAULT_ACTIVATION_TARGET)
    parser.add_argument(
        "--activation-base-quota",
        type=int,
        default=DEFAULT_ACTIVATION_BASE_QUOTA,
    )
    parser.add_argument(
        "--activation-first-batch-size",
        type=int,
        default=DEFAULT_ACTIVATION_FIRST_BATCH,
    )
    parser.add_argument(
        "--activation-batch-size",
        type=int,
        default=DEFAULT_ACTIVATION_BATCH_SIZE,
    )
    args = parser.parse_args()

    result = run_label_export_cli(
        settings=settings,
        cli_input=LabelExportCliInput(
            output_dir=Path(args.output_dir),
            post_limit=int(args.post_limit),
            comment_limit=int(args.comment_limit),
            lookback_days=int(args.lookback_days),
            export_all=bool(args.export_all),
            include_noise=bool(args.include_noise),
            noise_ratio=float(args.noise_ratio),
            noise_min_score=int(args.noise_min_score),
            noise_min_comments=int(args.noise_min_comments),
            top_comments=int(args.top_comments),
            posts_only=bool(args.posts_only),
            comments_only=bool(args.comments_only),
            historical_activation=bool(args.historical_activation),
            activation_target=int(args.activation_target),
            activation_base_quota=int(args.activation_base_quota),
            activation_first_batch_size=int(args.activation_first_batch_size),
            activation_batch_size=int(args.activation_batch_size),
        ),
    )
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
