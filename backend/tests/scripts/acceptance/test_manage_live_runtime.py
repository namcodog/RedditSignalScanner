from __future__ import annotations

from pathlib import Path

from scripts.acceptance.manage_live_runtime import (
    DEFAULT_BULK_QUEUES,
    LiveRuntimeConfig,
    ProcessSpec,
    build_process_specs,
    parse_args,
    summarize_runtime_status,
)


def _config() -> LiveRuntimeConfig:
    return LiveRuntimeConfig(
        backend_port=8016,
        analysis_concurrency=2,
        bulk_concurrency=2,
        bulk_queues=DEFAULT_BULK_QUEUES,
        warmup_base_delay_seconds=90,
        warmup_max_delay_seconds=300,
        backfill_settle_seconds=20,
        backfill_max_targets=120,
    )


def test_parse_args_supports_runtime_defaults() -> None:
    args = parse_args(["status"])

    assert args.action == "status"
    assert args.backend_port == 8016
    assert args.bulk_queues == DEFAULT_BULK_QUEUES


def test_build_process_specs_uses_isolated_hostnames_and_port() -> None:
    specs = build_process_specs(_config(), python_bin="/tmp/python", hostname="node-a")

    backend_spec = next(spec for spec in specs if spec.name == "backend")
    analysis_spec = next(spec for spec in specs if spec.name == "analysis-live")
    bulk_spec = next(spec for spec in specs if spec.name == "bulk-live")

    assert "--port" in backend_spec.command
    assert "8016" in backend_spec.command
    assert "--hostname=analysis-live@node-a" in analysis_spec.command
    assert "--hostname=bulk-live@node-a" in bulk_spec.command
    assert analysis_spec.env_overrides["DISABLE_AUTO_CRAWL_BOOTSTRAP"] == "1"
    assert analysis_spec.env_overrides["ENABLE_CELERY_DISPATCH"] == "1"
    assert bulk_spec.env_overrides["DISABLE_AUTO_CRAWL_BOOTSTRAP"] == "1"


def test_summarize_runtime_status_flags_duplicates() -> None:
    specs = [
        ProcessSpec(
            name="analysis-live",
            command=(),
            env_overrides={},
            pid_file=Path("/tmp/analysis.pid"),
            log_file=Path("/tmp/analysis.log"),
            match_pattern="analysis-live@",
        ),
        ProcessSpec(
            name="bulk-live",
            command=(),
            env_overrides={},
            pid_file=Path("/tmp/bulk.pid"),
            log_file=Path("/tmp/bulk.log"),
            match_pattern="bulk-live@",
        ),
    ]

    pid_map = {
        Path("/tmp/analysis.pid"): 101,
        Path("/tmp/bulk.pid"): 202,
    }
    matched = {
        "analysis-live@": [101, 303],
        "bulk-live@": [202],
    }

    payload = summarize_runtime_status(
        specs,
        backend_port=8016,
        pid_reader=lambda path: pid_map.get(path),
        pid_alive=lambda pid: True,
        pgrep_pids=lambda pattern: matched.get(pattern, []),
        backend_ready=True,
    )

    assert payload["ok"] is False
    assert payload["duplicates_detected"] is True
    analysis_row = next(item for item in payload["processes"] if item["name"] == "analysis-live")
    assert analysis_row["duplicate_count"] == 1


def test_summarize_runtime_status_accepts_clean_single_instance() -> None:
    specs = [
        ProcessSpec(
            name="backend",
            command=(),
            env_overrides={},
            pid_file=Path("/tmp/backend.pid"),
            log_file=Path("/tmp/backend.log"),
            match_pattern="uvicorn app.main:app --host 127.0.0.1 --port 8016",
        )
    ]

    payload = summarize_runtime_status(
        specs,
        backend_port=8016,
        pid_reader=lambda _path: 404,
        pid_alive=lambda _pid: True,
        pgrep_pids=lambda _pattern: [404],
        backend_ready=True,
    )

    assert payload["ok"] is True
    assert payload["duplicates_detected"] is False
