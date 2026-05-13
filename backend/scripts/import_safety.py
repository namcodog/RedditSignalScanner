from __future__ import annotations

import argparse

from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError

from app.core.config import settings
from app.db.database_guard import validate_database_target

WRITABLE_DATABASE_NAMES = frozenset({"reddit_signal_scanner_dev", "reddit_signal_scanner_test"})


def ensure_dev_or_test_database(database_url: str | None = None) -> str:
    url = database_url or settings.database_url
    validate_database_target(url)
    try:
        db_name = make_url(url).database or ""
    except ArgumentError as exc:
        raise RuntimeError(f"Invalid database URL for import script: {url}") from exc
    if db_name not in WRITABLE_DATABASE_NAMES:
        raise RuntimeError(
            f"Import/restore scripts can only write to dev/test databases, got: {db_name or 'unknown'}"
        )
    return db_name


def add_execute_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--execute",
        action="store_true",
        help="实际写入数据库。默认只 dry-run，不会改库。",
    )


def is_dry_run(args: argparse.Namespace) -> bool:
    return not bool(getattr(args, "execute", False))
