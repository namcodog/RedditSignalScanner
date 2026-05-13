from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from app.core.config import Settings
from app.services.llm.label_export_service import (
    LabelExportWorkflowInput,
    run_label_export,
)
from app.services.llm.label_import_workflow import (
    LabelImportWorkflowInput,
    LabelImportWorkflowResult,
    import_label_files,
)


@dataclass(slots=True)
class LabelExportCliInput:
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


@dataclass(slots=True)
class LabelImportCliInput:
    posts_path: Path | None
    comments_path: Path | None
    batch_size: int
    llm_version: str
    model_name: str
    prompt_version: str
    database_url: str
    allow_gold: bool


def ensure_non_gold_database(*, database_url: str, allow_gold: bool) -> None:
    is_gold_db = (
        "reddit_signal_scanner" in database_url
        and "_dev" not in database_url
        and "_test" not in database_url
    )
    if is_gold_db and not allow_gold:
        raise SystemExit(
            "❌ 金库写保护：当前 DATABASE_URL 指向金库 (reddit_signal_scanner)。\n"
            "   离线导入脚本禁止写入金库。请切换到 Dev 库，或显式设置 ALLOW_GOLD_DB=1。"
        )


def run_label_export_cli(
    *,
    settings: Settings,
    cli_input: LabelExportCliInput,
) -> dict[str, Any]:
    return run_label_export(
        LabelExportWorkflowInput(
            output_dir=cli_input.output_dir,
            post_limit=cli_input.post_limit,
            comment_limit=cli_input.comment_limit,
            lookback_days=cli_input.lookback_days,
            export_all=cli_input.export_all,
            include_noise=cli_input.include_noise,
            noise_ratio=cli_input.noise_ratio,
            noise_min_score=cli_input.noise_min_score,
            noise_min_comments=cli_input.noise_min_comments,
            top_comments=cli_input.top_comments,
            posts_only=cli_input.posts_only,
            comments_only=cli_input.comments_only,
            historical_activation=cli_input.historical_activation,
            activation_target=cli_input.activation_target,
            activation_base_quota=cli_input.activation_base_quota,
            activation_first_batch_size=cli_input.activation_first_batch_size,
            activation_batch_size=cli_input.activation_batch_size,
            max_body_chars=int(settings.llm_label_body_chars),
            max_comment_chars=int(settings.llm_label_comment_chars),
        )
    )


async def run_label_import_cli(
    *,
    cli_input: LabelImportCliInput,
    progress_writer: Callable[[str], None] = print,
) -> LabelImportWorkflowResult:
    ensure_non_gold_database(
        database_url=cli_input.database_url,
        allow_gold=cli_input.allow_gold,
    )

    def _print_progress(kind: str, imported: int, total: int) -> None:
        progress_writer(f"[{kind}] imported {imported}/{total}")

    return await import_label_files(
        workflow_input=LabelImportWorkflowInput(
            posts_path=cli_input.posts_path,
            comments_path=cli_input.comments_path,
            batch_size=cli_input.batch_size,
            llm_version=cli_input.llm_version,
            model_name=cli_input.model_name,
            prompt_version=cli_input.prompt_version,
        ),
        progress_callback=_print_progress,
    )


__all__ = [
    "LabelExportCliInput",
    "LabelImportCliInput",
    "ensure_non_gold_database",
    "run_label_export_cli",
    "run_label_import_cli",
]
