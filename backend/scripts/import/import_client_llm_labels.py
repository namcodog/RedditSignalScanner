from __future__ import annotations

import argparse
import os
from pathlib import Path

from app.core.config import get_settings
from app.services.llm.label_io_runtime import (
    LabelImportCliInput,
    run_label_import_cli,
)
from app.utils.asyncio_runner import run as run_coro


async def _import_labels(
    *,
    posts_path: Path | None,
    comments_path: Path | None,
    batch_size: int,
    llm_version: str,
    model_name: str,
    prompt_version: str,
) -> None:
    settings = get_settings()
    await run_label_import_cli(
        cli_input=LabelImportCliInput(
            posts_path=posts_path,
            comments_path=comments_path,
            batch_size=batch_size,
            llm_version=llm_version,
            model_name=model_name,
            prompt_version=prompt_version,
            database_url=str(getattr(settings, "database_url", "") or ""),
            allow_gold=os.getenv("ALLOW_GOLD_DB", "0").strip() == "1",
        ),
        progress_writer=print,
    )


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--posts", type=Path, default=None)
    parser.add_argument("--comments", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--llm-version", default=settings.llm_label_prompt_version)
    parser.add_argument("--model-name", default=settings.llm_label_model_name)
    parser.add_argument("--prompt-version", default=settings.llm_label_prompt_version)
    args = parser.parse_args()

    run_coro(
        _import_labels(
            posts_path=args.posts,
            comments_path=args.comments,
            batch_size=max(1, int(args.batch_size)),
            llm_version=str(args.llm_version),
            model_name=str(args.model_name),
            prompt_version=str(args.prompt_version),
        )
    )


if __name__ == "__main__":
    main()
