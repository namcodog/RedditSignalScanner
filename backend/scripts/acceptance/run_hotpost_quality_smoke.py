#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.acceptance.run_live_hotpost_acceptance import (
    _json_request,
    _poll_result,
    _run_preflight,
    _validate_hotpost_payload,
)


@dataclass(frozen=True)
class SmokeCase:
    query: str
    mode: str
    time_filter: str | None = None


DEFAULT_CASES: tuple[SmokeCase, ...] = (
    SmokeCase(query="tiktok shop sellers", mode="trending", time_filter="month"),
    SmokeCase(query="shopify app bugs", mode="rant", time_filter="month"),
    SmokeCase(query="reddit scheduling tool", mode="opportunity", time_filter="month"),
)


def _parse_case(raw: str) -> SmokeCase:
    parts = [part.strip() for part in raw.split("|")]
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise argparse.ArgumentTypeError(
            "case must be formatted as 'query|mode' or 'query|mode|time_filter'",
        )
    time_filter = parts[2] if len(parts) > 2 and parts[2] else None
    return SmokeCase(query=parts[0], mode=parts[1], time_filter=time_filter)


def _resolve_cases(raw_cases: list[str], *, limit: int) -> list[SmokeCase]:
    if raw_cases:
        cases = [_parse_case(raw) for raw in raw_cases]
    else:
        cases = list(DEFAULT_CASES)
    if limit > 0:
        return cases[:limit]
    return cases


def _extract_case_result(
    payload: dict[str, Any],
    *,
    fallback_query: str,
    fallback_mode: str,
) -> dict[str, Any]:
    debug_info = payload.get("debug_info")
    if hasattr(debug_info, "model_dump"):
        debug = debug_info.model_dump()
    elif isinstance(debug_info, dict):
        debug = dict(debug_info)
    else:
        debug = {}

    quality_gaps = [str(gap).strip() for gap in debug.get("quality_contract_gaps") or [] if str(gap).strip()]
    degraded_reasons = [
        str(reason).strip() for reason in debug.get("degraded_reasons") or [] if str(reason).strip()
    ]

    return {
        "query_id": str(payload.get("query_id") or "").strip(),
        "query": payload.get("query") or fallback_query,
        "mode": str(payload.get("mode") or fallback_mode).strip().lower(),
        "status": str(payload.get("status") or "completed").strip().lower(),
        "summary": str(payload.get("summary") or "").strip(),
        "evidence_count": int(payload.get("evidence_count") or 0),
        "community_count": len(payload.get("communities") or []),
        "quality_gap_count": len(quality_gaps),
        "quality_contract_gaps": quality_gaps,
        "degraded_reasons": degraded_reasons,
        "reasoning_triggered": bool(debug.get("reasoning_triggered")),
        "final_report_layer": str(debug.get("final_report_layer") or "fast").strip().lower(),
        "report_model_name": str(debug.get("report_model_name") or "").strip(),
        "fast_model_name": str(debug.get("fast_model_name") or "").strip(),
        "reasoning_model_name": str(debug.get("reasoning_model_name") or "").strip(),
        "report_source": str(debug.get("report_source") or "").strip().lower(),
        "report_degraded_reason": str(debug.get("report_degraded_reason") or "").strip().lower(),
    }


def _build_summary(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    evidence_counts = [int(item["evidence_count"]) for item in case_results]
    layer_counts: dict[str, int] = {}
    report_source_counts: dict[str, int] = {}
    degraded_cases = 0
    reasoning_cases = 0
    total_gaps = 0

    for item in case_results:
        layer = str(item["final_report_layer"] or "unknown")
        layer_counts[layer] = layer_counts.get(layer, 0) + 1
        report_source = str(item["report_source"] or "unknown")
        report_source_counts[report_source] = report_source_counts.get(report_source, 0) + 1
        total_gaps += int(item["quality_gap_count"])
        if item["reasoning_triggered"]:
            reasoning_cases += 1
        if item["status"] == "degraded" or item["degraded_reasons"]:
            degraded_cases += 1

    return {
        "total_cases": len(case_results),
        "reasoning_triggered_cases": reasoning_cases,
        "fast_only_cases": len(case_results) - reasoning_cases,
        "degraded_cases": degraded_cases,
        "total_quality_gap_count": total_gaps,
        "avg_evidence_count": round(statistics.mean(evidence_counts), 2) if evidence_counts else 0,
        "min_evidence_count": min(evidence_counts) if evidence_counts else 0,
        "max_evidence_count": max(evidence_counts) if evidence_counts else 0,
        "final_report_layers": layer_counts,
        "report_sources": report_source_counts,
        "estimated_reasoning_uplift_requests": reasoning_cases,
    }


def _run_case(
    *,
    base_url: str,
    case: SmokeCase,
    timeout_seconds: int,
    poll_interval: float,
    request_timeout_seconds: float,
    request_retry_attempts: int,
    request_retry_delay_seconds: float,
) -> dict[str, Any]:
    request_payload: dict[str, Any] = {
        "query": case.query,
        "mode": case.mode,
    }
    if case.time_filter:
        request_payload["time_filter"] = case.time_filter

    search_payload = _json_request(
        f"{base_url}/api/hotpost/search",
        request_payload,
        timeout_seconds=request_timeout_seconds,
        retry_attempts=request_retry_attempts,
        retry_delay_seconds=request_retry_delay_seconds,
    )
    query_id = str(search_payload["query_id"])
    status = str(search_payload.get("status") or "completed").strip().lower()

    if status in {"queued", "processing"}:
        result_payload = _poll_result(
            base_url,
            query_id,
            timeout_seconds=timeout_seconds,
            interval_seconds=poll_interval,
            request_timeout_seconds=request_timeout_seconds,
            request_retry_attempts=request_retry_attempts,
            request_retry_delay_seconds=request_retry_delay_seconds,
        )
    else:
        result_payload = search_payload

    issues = _validate_hotpost_payload(result_payload)
    if issues:
        raise RuntimeError(
            f"Hotpost acceptance payload invalid for {case.mode}:{case.query}: {'; '.join(issues)}",
        )

    return _extract_case_result(
        result_payload,
        fallback_query=case.query,
        fallback_mode=case.mode,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a low-cost live hotpost quality smoke")
    parser.add_argument("--base-url", default="http://127.0.0.1:8006")
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help="Custom case in format 'query|mode' or 'query|mode|time_filter'",
    )
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--request-retry-attempts", type=int, default=3)
    parser.add_argument("--request-retry-delay-seconds", type=float, default=2.0)
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()

    cases = _resolve_cases(args.case, limit=args.limit)
    if not cases:
        raise RuntimeError("No smoke cases selected")

    preflight: dict[str, Any] | None = None
    if not args.skip_preflight:
        preflight = _run_preflight(
            args.base_url,
            request_timeout_seconds=args.request_timeout_seconds,
        )

    case_results: list[dict[str, Any]] = []
    for case in cases:
        case_results.append(
            _run_case(
                base_url=args.base_url,
                case=case,
                timeout_seconds=args.timeout_seconds,
                poll_interval=args.poll_interval,
                request_timeout_seconds=args.request_timeout_seconds,
                request_retry_attempts=args.request_retry_attempts,
                request_retry_delay_seconds=args.request_retry_delay_seconds,
            )
        )

    output = {
        "smoke_type": "hotpost_quality_low_cost",
        "base_url": args.base_url,
        "preflight": preflight,
        "summary": _build_summary(case_results),
        "cases": case_results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - acceptance utility
        print(f"run_hotpost_quality_smoke failed: {exc}", file=sys.stderr)
        raise
