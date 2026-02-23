from __future__ import annotations

import pytest

from app.db.database_guard import validate_database_target


def test_blocks_gold_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("ALLOW_GOLD_DB", raising=False)

    with pytest.raises(RuntimeError, match="(?i)gold|reddit_signal_scanner"):
        validate_database_target(
            "postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner"
        )


def test_allows_gold_with_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ALLOW_GOLD_DB", "1")

    validate_database_target(
        "postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner"
    )


def test_allows_gold_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ALLOW_GOLD_DB", raising=False)

    validate_database_target(
        "postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner"
    )


def test_allows_dev_and_test_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("ALLOW_GOLD_DB", raising=False)

    validate_database_target(
        "postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner_dev"
    )
    validate_database_target(
        "postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner_test"
    )
