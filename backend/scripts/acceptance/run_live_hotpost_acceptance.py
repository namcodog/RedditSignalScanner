#!/usr/bin/env python3
from __future__ import annotations

"""
Trigger a fresh hotpost search and poll until the result is ready.

Use this script for product acceptance when historical hotpost result ids are no
longer reliable because cached `/api/hotpost/result/{id}` entries may expire.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import socket
from typing import Any


def _json_request(
    url: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout_seconds: float,
    retry_attempts: int,
    retry_delay_seconds: float,
) -> dict[str, Any]:
    body = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(url=url, data=body, headers=headers)
    last_error: Exception | None = None

    for attempt in range(1, retry_attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError:
            raise
        except (TimeoutError, urllib.error.URLError, socket.timeout) as exc:
            last_error = exc
            if attempt >= retry_attempts:
                raise
            time.sleep(retry_delay_seconds)

    raise RuntimeError(f"request failed for {url}: {last_error}")


def _poll_result(
    base_url: str,
    query_id: str,
    timeout_seconds: int,
    interval_seconds: float,
    request_timeout_seconds: float,
    request_retry_attempts: int,
    request_retry_delay_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    result_url = f"{base_url}/api/hotpost/result/{query_id}"
    last_error: str | None = None

    while time.monotonic() < deadline:
        try:
            payload = _json_request(
                result_url,
                timeout_seconds=request_timeout_seconds,
                retry_attempts=request_retry_attempts,
                retry_delay_seconds=request_retry_delay_seconds,
            )
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"
            if exc.code != 404:
                raise
        else:
            status = str(payload.get("status") or "completed")
            if status not in {"queued", "processing"}:
                return payload
        time.sleep(interval_seconds)

    raise TimeoutError(f"Timed out waiting for hotpost result {query_id}. Last error: {last_error or 'none'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a fresh live hotpost acceptance query")
    parser.add_argument("--base-url", default="http://127.0.0.1:8006")
    parser.add_argument("--query", default="tiktok shop sellers")
    parser.add_argument("--mode", default="trending")
    parser.add_argument("--time-filter", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--request-retry-attempts", type=int, default=3)
    parser.add_argument("--request-retry-delay-seconds", type=float, default=2.0)
    args = parser.parse_args()

    payload = {
        "query": args.query,
        "mode": args.mode,
    }
    if args.time_filter:
        payload["time_filter"] = args.time_filter

    search_payload = _json_request(
        f"{args.base_url}/api/hotpost/search",
        payload,
        timeout_seconds=args.request_timeout_seconds,
        retry_attempts=args.request_retry_attempts,
        retry_delay_seconds=args.request_retry_delay_seconds,
    )
    query_id = str(search_payload["query_id"])
    status = str(search_payload.get("status") or "completed")

    if status in {"queued", "processing"}:
        result_payload = _poll_result(
            args.base_url,
            query_id,
            timeout_seconds=args.timeout_seconds,
            interval_seconds=args.poll_interval,
            request_timeout_seconds=args.request_timeout_seconds,
            request_retry_attempts=args.request_retry_attempts,
            request_retry_delay_seconds=args.request_retry_delay_seconds,
        )
    else:
        result_payload = search_payload

    output = {
        "query_id": query_id,
        "query": result_payload.get("query") or args.query,
        "mode": result_payload.get("mode") or args.mode,
        "status": result_payload.get("status") or "completed",
        "evidence_count": result_payload.get("evidence_count"),
        "community_count": len(result_payload.get("communities") or []),
        "summary": result_payload.get("summary"),
        "result_url": f"http://127.0.0.1:3006/hotpost/result/{query_id}",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - acceptance utility
        print(f"run_live_hotpost_acceptance failed: {exc}", file=sys.stderr)
        raise
