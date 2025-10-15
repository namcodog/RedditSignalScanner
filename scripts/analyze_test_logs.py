#!/usr/bin/env python3
"""Analyze test execution logs and emit performance metrics."""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class TestRun:
    timestamp: str
    test: str
    status: str
    duration_seconds: float


def _parse_duration(value: str) -> Optional[float]:
    token = value.strip().lower().replace("duration=", "")
    if token.endswith("s"):
        token = token[:-1]
    try:
        return float(token)
    except ValueError:
        return None


def _parse_line(line: str) -> Optional[TestRun]:
    if not line.strip():
        return None

    if "|" in line:
        parts = [part.strip() for part in line.split("|")]
    else:
        parts = line.split()

    if len(parts) < 4:
        return None

    timestamp = parts[0]
    test_name = parts[1]
    status = parts[2].lower()
    duration = None

    for part in reversed(parts):
        duration = _parse_duration(part)
        if duration is not None:
            break

    if duration is None:
        return None

    return TestRun(timestamp=timestamp, test=test_name, status=status, duration_seconds=duration)


def analyze_runs(runs: Iterable[TestRun]) -> dict:
    runs_list = list(runs)
    if not runs_list:
        return {
            "runs": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "failure_rate": 0.0,
                "avg_duration": 0.0,
                "median_duration": 0.0,
                "p95_duration": 0.0,
                "max_duration": 0.0,
            },
        }

    durations = [run.duration_seconds for run in runs_list]
    passed = sum(1 for run in runs_list if run.status == "success")
    failed = len(runs_list) - passed
    failure_rate = failed / len(runs_list)

    p95 = statistics.quantiles(durations, n=100)[94] if len(durations) >= 2 else durations[0]

    summary = {
        "total": len(runs_list),
        "passed": passed,
        "failed": failed,
        "failure_rate": failure_rate,
        "avg_duration": statistics.mean(durations),
        "median_duration": statistics.median(durations),
        "p95_duration": p95,
        "max_duration": max(durations),
    }

    return {
        "runs": [run.__dict__ for run in runs_list],
        "summary": summary,
    }


def _write_markdown(path: Path, data: dict) -> None:
    summary = data.get("summary", {})
    lines = [
        "## 端到端测试性能摘要",
        "",
        f"- 总执行次数: {summary.get('total', 0)}",
        f"- 成功次数: {summary.get('passed', 0)}",
        f"- 失败次数: {summary.get('failed', 0)}",
        f"- 失败率: {summary.get('failure_rate', 0.0):.2%}",
        f"- 平均耗时: {summary.get('avg_duration', 0.0):.2f}s",
        f"- 中位耗时: {summary.get('median_duration', 0.0):.2f}s",
        f"- P95 耗时: {summary.get('p95_duration', 0.0):.2f}s",
        f"- 最大耗时: {summary.get('max_duration', 0.0):.2f}s",
        "",
        "> 说明：数据来源于测试日志自动解析，如需更详细的趋势分析，请结合 Grafana/Redis 指标。",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze end-to-end test logs")
    parser.add_argument("log_path", nargs="?", default="tmp/test_runs/e2e.log")
    parser.add_argument("--metrics-out", default="tmp/test_runs/e2e_metrics.json")
    parser.add_argument("--markdown-out", default=None)
    args = parser.parse_args()

    log_file = Path(args.log_path)
    if not log_file.exists():
        raise SystemExit(f"Log file not found: {log_file}")

    runs: List[TestRun] = []
    with log_file.open(encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            parsed = _parse_line(line)
            if parsed is not None:
                runs.append(parsed)

    analysis = analyze_runs(runs)
    metrics_path = Path(args.metrics_out)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.markdown_out:
        _write_markdown(Path(args.markdown_out), analysis)

    print(json.dumps(analysis, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
