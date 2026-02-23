#!/usr/bin/env python3
"""
智能工作流：根据本地生产库状态，建议/启动 Celery（Beat + 分队列 Worker）。

默认只打印建议（dry-run），不会启动任何进程。

用法：
  # 只看现状 + 建议（不启动）
  PYTHONPATH=backend python backend/scripts/smart_crawler_workflow.py

  # 按建议启动（Beat + patrol + bulk；probe 视开关）
  PYTHONPATH=backend python backend/scripts/smart_crawler_workflow.py --apply
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

try:
    import psycopg
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "❌ 缺少依赖 psycopg。\n"
        "   建议用 venv 跑：`.venv/bin/python backend/scripts/smart_crawler_workflow.py`"
    ) from exc

# Ensure `import app.*` works when invoked from repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.ops.smart_crawler_workflow import (  # noqa: E402
    DbSnapshot,
    EnvFlags,
    WorkflowDecision,
    decide_workflow,
)


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        # strip optional quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        data[key] = value
    return data


def _bool_env(env: dict[str, str], key: str, default: bool = False) -> bool:
    raw = (env.get(key) or os.getenv(key) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y", "on"}


def _normalize_postgres_dsn(raw: str) -> str:
    """Convert SQLAlchemy-style URLs to psycopg DSN."""
    if raw.startswith("postgresql+asyncpg://"):
        return "postgresql://" + raw.removeprefix("postgresql+asyncpg://")
    if raw.startswith("postgresql+psycopg://"):
        return "postgresql://" + raw.removeprefix("postgresql+psycopg://")
    return raw


def _query_one(
    cursor: psycopg.Cursor[tuple[object, ...]],
    sql: str,
) -> tuple[object, ...]:
    cursor.execute(sql)
    row = cursor.fetchone()
    if row is None:
        return tuple()
    return tuple(row)


def _to_int(value: object) -> int:
    if value is None:
        return 0
    return int(value)


def _to_dt(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    raise TypeError(f"Unexpected datetime value: {type(value)}")


def _gather_db_snapshot(*, dsn: str) -> DbSnapshot:
    now = datetime.now(timezone.utc)
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            posts_raw_newest = _to_dt(_query_one(cur, "select max(fetched_at) from posts_raw;")[0])
            posts_hot_newest = _to_dt(_query_one(cur, "select max(cached_at) from posts_hot;")[0])
            comments_newest = _to_dt(_query_one(cur, "select max(fetched_at) from comments;")[0])

            posts_raw_24h = _to_int(
                _query_one(cur, "select count(*) from posts_raw where fetched_at > now() - interval '24 hours';")[0]
            )
            posts_hot_24h = _to_int(
                _query_one(cur, "select count(*) from posts_hot where cached_at > now() - interval '24 hours';")[0]
            )
            comments_24h = _to_int(
                _query_one(cur, "select count(*) from comments where fetched_at > now() - interval '24 hours';")[0]
            )

            cache_total, cache_active, never_crawled, stale_24h = (
                _query_one(
                    cur,
                    "select "
                    "count(*) as total, "
                    "count(*) filter (where is_active) as active_total, "
                    "count(*) filter (where last_crawled_at is null) as never_crawled, "
                    "count(*) filter (where last_crawled_at < now() - interval '24 hours') as stale_24h "
                    "from community_cache;",
                )
                or (0, 0, 0, 0)
            )

            pool_total = _to_int(
                _query_one(cur, "select count(*) from community_pool where deleted_at is null;")[0]
            )
            pool_active = _to_int(
                _query_one(
                    cur,
                    "select count(*) from community_pool where deleted_at is null and is_active;",
                )[0]
            )
            pool_missing_cache = _to_int(
                _query_one(
                    cur,
                    "select count(*) "
                    "from community_pool p "
                    "left join community_cache c on c.community_name=p.name "
                    "where p.deleted_at is null and c.community_name is null;",
                )[0]
            )

            crawler_runs_total = _to_int(_query_one(cur, "select count(*) from crawler_runs;")[0])
            crawler_targets_total = _to_int(_query_one(cur, "select count(*) from crawler_run_targets;")[0])

            discovered_total = _to_int(_query_one(cur, "select count(*) from discovered_communities;")[0])
            evidence_total = _to_int(_query_one(cur, "select count(*) from evidence_posts;")[0])

    return DbSnapshot(
        now=now,
        posts_raw_newest_fetched_at=posts_raw_newest,
        posts_hot_newest_cached_at=posts_hot_newest,
        comments_newest_fetched_at=comments_newest,
        posts_raw_fetched_24h=posts_raw_24h,
        posts_hot_cached_24h=posts_hot_24h,
        comments_fetched_24h=comments_24h,
        community_cache_total=_to_int(cache_total),
        community_cache_active_total=_to_int(cache_active),
        community_cache_never_crawled=_to_int(never_crawled),
        community_cache_stale_24h=_to_int(stale_24h),
        pool_total=pool_total,
        pool_active_total=pool_active,
        pool_missing_cache=pool_missing_cache,
        crawler_runs_total=crawler_runs_total,
        crawler_run_targets_total=crawler_targets_total,
        discovered_communities_total=discovered_total,
        evidence_posts_total=evidence_total,
    )


def _format_dt(value: datetime | None) -> str:
    if value is None:
        return "(none)"
    return value.astimezone(timezone.utc).isoformat()


def _print_snapshot(snapshot: DbSnapshot) -> None:
    print("=== DB 现状快照（本地生产库）===")
    print(f"- posts_raw 最新: {_format_dt(snapshot.posts_raw_newest_fetched_at)} (24h新增={snapshot.posts_raw_fetched_24h})")
    print(f"- posts_hot 最新: {_format_dt(snapshot.posts_hot_newest_cached_at)} (24h新增={snapshot.posts_hot_cached_24h})")
    print(f"- comments  最新: {_format_dt(snapshot.comments_newest_fetched_at)} (24h新增={snapshot.comments_fetched_24h})")
    print(
        "- community_cache: "
        f"total={snapshot.community_cache_total} active={snapshot.community_cache_active_total} "
        f"never={snapshot.community_cache_never_crawled} stale_24h={snapshot.community_cache_stale_24h}"
    )
    print(
        "- community_pool: "
        f"total={snapshot.pool_total} active={snapshot.pool_active_total} missing_cache={snapshot.pool_missing_cache}"
    )
    print(
        "- run/targets: "
        f"crawler_runs={snapshot.crawler_runs_total} crawler_run_targets={snapshot.crawler_run_targets_total}"
    )
    print(
        "- probe资产: "
        f"discovered_communities={snapshot.discovered_communities_total} evidence_posts={snapshot.evidence_posts_total}"
    )
    print("")


def _celery_process_lines() -> list[str]:
    result = subprocess.run(
        ["pgrep", "-af", "celery"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        return []
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines


def _has_any(lines: Iterable[str], *needles: str) -> bool:
    for line in lines:
        if all(needle in line for needle in needles):
            return True
    return False


def _is_beat_running(lines: list[str]) -> bool:
    # 独立 beat: "... celery ... beat ..."
    if _has_any(lines, "celery", " beat "):
        return True
    # 内嵌 beat: "... celery ... worker --beat ..."
    return _has_any(lines, "celery", " worker", "--beat")


def _is_worker_running(lines: list[str], *, queue_marker: str) -> bool:
    return _has_any(lines, "celery", " worker", queue_marker)


def _spawn(
    *,
    name: str,
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    log_path: Path,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as logf:
        logf.write(f"\n\n===== {name} start at {datetime.now(timezone.utc).isoformat()} =====\n")
        logf.flush()
        subprocess.Popen(  # noqa: S603
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=logf,
            stderr=logf,
            start_new_session=True,
        )


def _apply_startup(*, decision: WorkflowDecision, env: dict[str, str]) -> None:
    logs_dir = REPO_ROOT / "logs"
    python_bin = sys.executable

    # Celery commands run in backend/ so `import app` works.
    base_env = os.environ.copy()
    base_env.update(env)
    base_env["PYTHONPATH"] = str(BACKEND_DIR)
    base_env.setdefault("NO_PROXY", "localhost,127.0.0.1,::1")
    base_env.setdefault("no_proxy", "localhost,127.0.0.1,::1")

    processes = _celery_process_lines()

    if decision.start_beat and not _is_beat_running(processes):
        print("- 启动 Celery Beat（调度器）...")
        _spawn(
            name="celery_beat",
            cmd=[python_bin, "-m", "celery", "-A", "app.core.celery_app:celery_app", "beat", "--loglevel=info"],
            cwd=BACKEND_DIR,
            env=base_env,
            log_path=logs_dir / "celery_beat.log",
        )
    else:
        print("- Beat 已在跑（跳过）")

    if decision.start_patrol_worker and not _is_worker_running(processes, queue_marker="patrol_queue"):
        print("- 启动 patrol worker（只吃 patrol_queue，保底供货）...")
        patrol_env = dict(base_env)
        patrol_concurrency = str(env.get("PATROL_WORKER_CONCURRENCY") or "4")
        _spawn(
            name="celery_patrol",
            cmd=[
                python_bin,
                "-m",
                "celery",
                "-A",
                "app.core.celery_app:celery_app",
                "worker",
                "--loglevel=info",
                "--pool=solo",
                "--concurrency",
                patrol_concurrency,
                "--queues=patrol_queue",
            ],
            cwd=BACKEND_DIR,
            env=patrol_env,
            log_path=logs_dir / "celery_patrol.log",
        )
    else:
        print("- patrol worker 已在跑（跳过）")

    if decision.start_bulk_worker and not _is_worker_running(processes, queue_marker="backfill_posts_queue_v2"):
        print("- 启动 bulk worker（backfill/compensation/maintenance/crawler/...）...")
        bulk_env = dict(base_env)
        bulk_env.setdefault("DISABLE_AUTO_CRAWL_BOOTSTRAP", "1")
        bulk_concurrency = str(env.get("BULK_WORKER_CONCURRENCY") or "2")
        queue_list = env.get(
            "BULK_QUEUE_LIST",
            "backfill_posts_queue_v2,backfill_queue,compensation_queue,analysis_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue",
        )
        _spawn(
            name="celery_bulk",
            cmd=[
                python_bin,
                "-m",
                "celery",
                "-A",
                "app.core.celery_app:celery_app",
                "worker",
                "--loglevel=info",
                "--pool=solo",
                "--concurrency",
                bulk_concurrency,
                f"--queues={queue_list}",
            ],
            cwd=BACKEND_DIR,
            env=bulk_env,
            log_path=logs_dir / "celery_bulk.log",
        )
    else:
        print("- bulk worker 已在跑（跳过）")

    if decision.start_probe_worker and not _is_worker_running(processes, queue_marker="probe_queue"):
        print("- 启动 probe worker（只吃 probe_queue）...")
        probe_env = dict(base_env)
        probe_env.setdefault("DISABLE_AUTO_CRAWL_BOOTSTRAP", "1")
        probe_concurrency = str(env.get("PROBE_WORKER_CONCURRENCY") or "1")
        _spawn(
            name="celery_probe",
            cmd=[
                python_bin,
                "-m",
                "celery",
                "-A",
                "app.core.celery_app:celery_app",
                "worker",
                "--loglevel=info",
                "--pool=solo",
                "--concurrency",
                probe_concurrency,
                "--queues=probe_queue",
            ],
            cwd=BACKEND_DIR,
            env=probe_env,
            log_path=logs_dir / "celery_probe.log",
        )
    elif decision.start_probe_worker:
        print("- probe worker 已在跑（跳过）")
    else:
        print("- probe worker 本轮不启动（按当前 DB 状况/开关建议先不跑 probe）")

    print("")
    print("日志位置：")
    print(f"- {logs_dir / 'celery_beat.log'}")
    print(f"- {logs_dir / 'celery_patrol.log'}")
    print(f"- {logs_dir / 'celery_bulk.log'}")
    print(f"- {logs_dir / 'celery_probe.log'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="智能启动 Celery（按 DB 现状给建议/可一键启动）")
    parser.add_argument("--apply", action="store_true", help="真正启动 Celery 进程（默认只打印建议）")
    parser.add_argument("--dsn", type=str, default="", help="覆盖 DATABASE_URL（用于临时切库）")
    args = parser.parse_args()

    backend_env_path = BACKEND_DIR / ".env"
    env = _parse_env_file(backend_env_path)

    dsn = args.dsn.strip() or env.get("DATABASE_URL") or os.getenv("DATABASE_URL") or ""
    if not dsn:
        raise SystemExit("❌ 找不到 DATABASE_URL（backend/.env 或环境变量里都没有）")
    dsn = _normalize_postgres_dsn(dsn)

    snapshot = _gather_db_snapshot(dsn=dsn)

    flags = EnvFlags(
        probe_hot_beat_enabled=_bool_env(env, "PROBE_HOT_BEAT_ENABLED", default=True),
        probe_auto_evaluate_enabled=_bool_env(env, "PROBE_AUTO_EVALUATE_ENABLED", default=True),
        cron_discovery_enabled=_bool_env(env, "CRON_DISCOVERY_ENABLED", default=True),
        comments_backfill_subs_configured=bool((env.get("COMMENTS_BACKFILL_SUBS") or "").strip()),
    )

    decision = decide_workflow(snapshot=snapshot, flags=flags)
    _print_snapshot(snapshot)

    print("=== 建议怎么启动（按现状自动给的）===")
    print(f"- Beat:   {'启动' if decision.start_beat else '不需要'}")
    print(f"- Patrol: {'启动' if decision.start_patrol_worker else '不需要'}")
    print(f"- Bulk:   {'启动' if decision.start_bulk_worker else '不需要'}")
    print(f"- Probe:  {'启动' if decision.start_probe_worker else '先不启动'}")
    print("")
    for note in decision.notes:
        print(f"- 说明：{note}")
    print("")

    if not args.apply:
        print("（dry-run）没启动任何进程。要一键启动：加 --apply")
        return

    print("=== 开始启动 Celery（按建议）===")
    _apply_startup(decision=decision, env=env)

    # 给产品/运营看的“下一步检查”
    print("")
    print("=== 下一步你该看什么（最省事版）===")
    print("- 1~3 分钟后跑一次：`psql -d reddit_signal_scanner_dev -c \"select max(fetched_at) from posts_raw;\"`")
    print("- 如果时间没往前走：先看 `logs/celery_patrol.log`（Reddit 凭证/429/网络/异常都会在这）")


if __name__ == "__main__":
    main()
