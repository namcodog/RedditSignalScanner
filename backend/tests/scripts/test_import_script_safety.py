from __future__ import annotations

import importlib

import pytest

from scripts.import_safety import ensure_dev_or_test_database


def _load_module(name: str):
    return importlib.import_module(name)


def test_import_scripts_block_gold_database() -> None:
    with pytest.raises(RuntimeError, match="(?i)(gold|dev/test|blocked)"):
        ensure_dev_or_test_database(
            "postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner"
        )


def test_import_scripts_allow_dev_and_test_databases() -> None:
    assert (
        ensure_dev_or_test_database(
            "postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner_dev"
        )
        == "reddit_signal_scanner_dev"
    )
    assert (
        ensure_dev_or_test_database(
            "postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner_test"
        )
        == "reddit_signal_scanner_test"
    )


def test_crossborder_import_parser_defaults_to_dry_run() -> None:
    mod = _load_module("backend.scripts.import.import_166_crossborder_communities")
    args = mod.build_parser().parse_args([])
    assert args.execute is False


def test_hybrid_import_parser_defaults_to_dry_run() -> None:
    mod = _load_module("backend.scripts.import.import_hybrid_scores_to_pool")
    args = mod.build_parser().parse_args([])
    assert args.execute is False


def test_restore_parser_defaults_to_dry_run_and_blocks_ghosts() -> None:
    mod = _load_module("backend.scripts.import.restore_pool_hybrid")
    args = mod.build_parser().parse_args([])
    assert args.execute is False
    assert args.allow_ghost_recovery is False


@pytest.mark.asyncio
async def test_restore_process_skips_ghost_recovery_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_module("backend.scripts.import.restore_pool_hybrid")

    monkeypatch.setattr(
        mod,
        "read_csv_config",
        lambda: {
            "alpha": {"name": "r/alpha", "tier": "high", "priority": "high", "source": "csv"}
        },
    )

    async def _fake_scan(_db):
        return {
            "alpha": {"raw_name": "alpha", "count": 10, "last_seen": None, "last_fetched": None},
            "ghost": {"raw_name": "ghost", "count": 200, "last_seen": None, "last_fetched": None},
        }

    monkeypatch.setattr(mod, "scan_database_assets", _fake_scan)

    upserted_pool: list[str] = []
    upserted_cache: list[str] = []

    async def _fake_upsert_pool(_db, item):
        upserted_pool.append(item.name)

    async def _fake_upsert_cache(_db, item):
        upserted_cache.append(item.community_name)

    monkeypatch.setattr(mod, "upsert_pool", _fake_upsert_pool)
    monkeypatch.setattr(mod, "upsert_cache", _fake_upsert_cache)

    class _FakeDB:
        committed = False
        rolled_back = False

        async def commit(self) -> None:
            self.committed = True

        async def rollback(self) -> None:
            self.rolled_back = True

    db = _FakeDB()
    summary = await mod.restore_process(
        db,
        execute=False,
        allow_ghost_recovery=False,
    )

    assert summary["restored"] == 1
    assert summary["recovered"] == 0
    assert summary["ghosts_blocked"] == 1
    assert upserted_pool == []
    assert upserted_cache == []
    assert db.rolled_back is True
    assert db.committed is False
