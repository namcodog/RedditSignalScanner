#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = PROJECT_ROOT / "backend"
LOG_DIR = PROJECT_ROOT / "logs"
STATE_DIR = BACKEND_DIR / "tmp" / "live_runtime"
DEFAULT_BULK_QUEUES = "backfill_posts_queue_v2,backfill_queue,compensation_queue"


@dataclass(frozen=True)
class LiveRuntimeConfig:
    backend_port: int
    analysis_concurrency: int
    bulk_concurrency: int
    bulk_queues: str
    warmup_base_delay_seconds: int
    warmup_max_delay_seconds: int
    backfill_settle_seconds: int
    backfill_max_targets: int


@dataclass(frozen=True)
class ProcessSpec:
    name: str
    command: tuple[str, ...]
    env_overrides: Mapping[str, str]
    pid_file: Path
    log_file: Path
    match_pattern: str


def _python_bin() -> str:
    for candidate in (
        PROJECT_ROOT / ".venv" / "bin" / "python",
        PROJECT_ROOT / "venv" / "bin" / "python",
    ):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _load_backend_env() -> dict[str, str]:
    env = dict(os.environ)
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key in env:
                continue
            if value.startswith(("\"", "'")) and value.endswith(("\"", "'")):
                value = value[1:-1]
            env[key] = value
    env.setdefault("NO_PROXY", "localhost,127.0.0.1,::1")
    env.setdefault("no_proxy", "localhost,127.0.0.1,::1")
    return env


def build_process_specs(
    config: LiveRuntimeConfig,
    *,
    python_bin: str,
    hostname: str,
) -> list[ProcessSpec]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    return [
        ProcessSpec(
            name="backend",
            command=(
                python_bin,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(config.backend_port),
            ),
            env_overrides={"ENABLE_CELERY_DISPATCH": "1"},
            pid_file=STATE_DIR / "backend.pid",
            log_file=LOG_DIR / "backend_live_runtime.log",
            match_pattern=f"uvicorn app.main:app --host 127.0.0.1 --port {config.backend_port}",
        ),
        ProcessSpec(
            name="analysis-live",
            command=(
                python_bin,
                "-m",
                "celery",
                "-A",
                "app.core.celery_app",
                "worker",
                "--loglevel=info",
                "--pool=solo",
                "--concurrency",
                str(config.analysis_concurrency),
                "--queues=analysis_queue",
                f"--hostname=analysis-live@{hostname}",
            ),
            env_overrides={
                "ENABLE_CELERY_DISPATCH": "1",
                "DISABLE_AUTO_CRAWL_BOOTSTRAP": "1",
                "WARMUP_AUTO_RERUN_BASE_DELAY_SECONDS": str(
                    config.warmup_base_delay_seconds
                ),
                "WARMUP_AUTO_RERUN_MAX_DELAY_SECONDS": str(
                    config.warmup_max_delay_seconds
                ),
                "WARMUP_INLINE_BACKFILL_SETTLE_SECONDS": str(
                    config.backfill_settle_seconds
                ),
                "WARMUP_INLINE_BACKFILL_MAX_TARGETS": str(
                    config.backfill_max_targets
                ),
            },
            pid_file=STATE_DIR / "analysis-live.pid",
            log_file=LOG_DIR / "celery_analysis_live_runtime.log",
            match_pattern="analysis-live@",
        ),
        ProcessSpec(
            name="bulk-live",
            command=(
                python_bin,
                "-m",
                "celery",
                "-A",
                "app.core.celery_app",
                "worker",
                "--loglevel=info",
                "--pool=solo",
                "--concurrency",
                str(config.bulk_concurrency),
                f"--queues={config.bulk_queues}",
                f"--hostname=bulk-live@{hostname}",
            ),
            env_overrides={"DISABLE_AUTO_CRAWL_BOOTSTRAP": "1"},
            pid_file=STATE_DIR / "bulk-live.pid",
            log_file=LOG_DIR / "celery_bulk_live_runtime.log",
            match_pattern="bulk-live@",
        ),
    ]


def _read_pid(pid_file: Path) -> int | None:
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except (TypeError, ValueError):
        return None


def _write_pid(pid_file: Path, pid: int) -> None:
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid), encoding="utf-8")


def _remove_pid(pid_file: Path) -> None:
    try:
        pid_file.unlink()
    except FileNotFoundError:
        pass


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _pgrep_pids(pattern: str) -> list[int]:
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []
    if result.returncode not in {0, 1}:
        return []
    pids: list[int] = []
    for raw in result.stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            pids.append(int(raw))
        except ValueError:
            continue
    return pids


def summarize_runtime_status(
    specs: Sequence[ProcessSpec],
    *,
    backend_port: int,
    pid_reader: Callable[[Path], int | None] = _read_pid,
    pid_alive: Callable[[int], bool] = _pid_alive,
    pgrep_pids: Callable[[str], list[int]] = _pgrep_pids,
    backend_ready: bool | None = None,
) -> dict[str, Any]:
    processes: list[dict[str, Any]] = []
    duplicates = False
    all_alive = True

    for spec in specs:
        pid = pid_reader(spec.pid_file)
        alive = bool(pid and pid_alive(pid))
        matched = pgrep_pids(spec.match_pattern)
        duplicate_count = max(0, len(matched) - (1 if alive and pid in matched else 0))
        if duplicate_count > 0:
            duplicates = True
        if not alive:
            all_alive = False
        processes.append(
            {
                "name": spec.name,
                "pid": pid,
                "alive": alive,
                "matched_pids": matched,
                "duplicate_count": duplicate_count,
                "log_file": str(spec.log_file),
                "pid_file": str(spec.pid_file),
            }
        )

    if backend_ready is None:
        backend_ready = _check_backend_health(backend_port)

    ok = all_alive and backend_ready and not duplicates
    return {
        "ok": ok,
        "backend_port": backend_port,
        "backend_ready": backend_ready,
        "duplicates_detected": duplicates,
        "processes": processes,
    }


def _kill_pid(pid: int, *, grace_seconds: float = 5.0) -> None:
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return
        time.sleep(0.2)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except OSError:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            return


def _kill_matching_pattern(pattern: str, *, grace_seconds: float = 3.0) -> list[int]:
    matched = _pgrep_pids(pattern)
    for pid in matched:
        _kill_pid(pid, grace_seconds=grace_seconds)
    return matched


def _check_backend_health(port: int, *, timeout_seconds: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/v1/health", timeout=timeout_seconds
        ) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _spawn_process(spec: ProcessSpec, env: Mapping[str, str]) -> int:
    process_env = dict(env)
    process_env.update(spec.env_overrides)
    with spec.log_file.open("a", encoding="utf-8") as log_handle:
        proc = subprocess.Popen(
            list(spec.command),
            cwd=str(BACKEND_DIR),
            env=process_env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    _write_pid(spec.pid_file, proc.pid)
    return proc.pid


def _wait_until_ready(
    specs: Sequence[ProcessSpec],
    *,
    backend_port: int,
    timeout_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_status: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last_status = summarize_runtime_status(specs, backend_port=backend_port)
        if last_status["ok"]:
            return last_status
        time.sleep(1.0)
    return last_status


def _stop_runtime(specs: Sequence[ProcessSpec]) -> dict[str, Any]:
    stopped: list[str] = []
    swept: dict[str, list[int]] = {}
    for spec in specs:
        pid = _read_pid(spec.pid_file)
        if pid is not None:
            _kill_pid(pid)
            _remove_pid(spec.pid_file)
            stopped.append(spec.name)

    for spec in specs:
        swept[spec.name] = _kill_matching_pattern(spec.match_pattern)
        _remove_pid(spec.pid_file)

    remaining = {spec.name: _pgrep_pids(spec.match_pattern) for spec in specs}
    return {"stopped": stopped, "swept": swept, "remaining": remaining}


def _start_runtime(config: LiveRuntimeConfig, *, startup_timeout_seconds: float) -> dict[str, Any]:
    env = _load_backend_env()
    specs = build_process_specs(
        config,
        python_bin=_python_bin(),
        hostname=socket.gethostname(),
    )
    _stop_runtime(specs)
    for spec in specs:
        _spawn_process(spec, env)
    status = _wait_until_ready(
        specs,
        backend_port=config.backend_port,
        timeout_seconds=startup_timeout_seconds,
    )
    if not status["ok"]:
        raise RuntimeError(f"live runtime failed to become ready: {json.dumps(status, ensure_ascii=False)}")
    return status


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage isolated live acceptance runtime")
    parser.add_argument("action", choices=("start", "stop", "restart", "status"))
    parser.add_argument("--backend-port", type=int, default=8016)
    parser.add_argument("--analysis-concurrency", type=int, default=2)
    parser.add_argument("--bulk-concurrency", type=int, default=2)
    parser.add_argument("--bulk-queues", default=DEFAULT_BULK_QUEUES)
    parser.add_argument("--warmup-base-delay-seconds", type=int, default=90)
    parser.add_argument("--warmup-max-delay-seconds", type=int, default=300)
    parser.add_argument("--backfill-settle-seconds", type=int, default=20)
    parser.add_argument("--backfill-max-targets", type=int, default=120)
    parser.add_argument("--startup-timeout-seconds", type=float, default=25.0)
    parser.add_argument("--json-only", action="store_true")
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = LiveRuntimeConfig(
        backend_port=args.backend_port,
        analysis_concurrency=args.analysis_concurrency,
        bulk_concurrency=args.bulk_concurrency,
        bulk_queues=args.bulk_queues,
        warmup_base_delay_seconds=args.warmup_base_delay_seconds,
        warmup_max_delay_seconds=args.warmup_max_delay_seconds,
        backfill_settle_seconds=args.backfill_settle_seconds,
        backfill_max_targets=args.backfill_max_targets,
    )
    specs = build_process_specs(
        config,
        python_bin=_python_bin(),
        hostname=socket.gethostname(),
    )

    if args.action == "start":
        payload = _start_runtime(
            config,
            startup_timeout_seconds=args.startup_timeout_seconds,
        )
    elif args.action == "restart":
        _stop_runtime(specs)
        payload = _start_runtime(
            config,
            startup_timeout_seconds=args.startup_timeout_seconds,
        )
    elif args.action == "stop":
        payload = _stop_runtime(specs)
        payload["ok"] = all(not pids for pids in payload.get("remaining", {}).values())
    else:
        payload = summarize_runtime_status(specs, backend_port=config.backend_port)

    if not args.json_only:
        print("==> Live runtime")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.action == "stop":
        return 0 if payload.get("ok", False) else 2
    return 0 if payload.get("ok", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
