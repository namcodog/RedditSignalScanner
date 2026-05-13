#!/usr/bin/env python3
from __future__ import annotations

"""
Trigger a fresh live report run and assert the result reaches the expected tier.

Use this script when product acceptance must verify the real chain:
login -> /api/analyze -> /api/status -> /api/report.
"""

import argparse
import json
import socket
import sys
import time
import urllib.error
import urllib.request
from typing import Any


DEFAULT_PRODUCT_DESCRIPTION = (
    "跨境电商卖家多平台回款与手续费管理工具，覆盖 Amazon/Etsy/Shopify/TikTok Shop，"
    "解决结算周期长、费率不透明、资金分散的问题。"
)


def _extract_http_error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8")
    except Exception:  # pragma: no cover - defensive
        return exc.reason if isinstance(exc.reason, str) else str(exc.reason)

    if not raw.strip():
        return exc.reason if isinstance(exc.reason, str) else str(exc.reason)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw.strip()

    detail = payload.get("detail")
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    return raw.strip()


def _json_request(
    url: str,
    payload: dict[str, Any] | None = None,
    *,
    headers: dict[str, str] | None = None,
    timeout_seconds: float,
    retry_attempts: int,
    retry_delay_seconds: float,
) -> dict[str, Any]:
    body = None
    request_headers: dict[str, str] = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(url=url, data=body, headers=request_headers)

    for attempt in range(1, retry_attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError:
            raise
        except (TimeoutError, urllib.error.URLError, socket.timeout):
            if attempt >= retry_attempts:
                raise
            time.sleep(retry_delay_seconds)

    raise RuntimeError(f"request failed for {url}")


def _poll_status(
    *,
    base_url: str,
    task_id: str,
    auth_headers: dict[str, str],
    timeout_seconds: int,
    interval_seconds: float,
    request_timeout_seconds: float,
    request_retry_attempts: int,
    request_retry_delay_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    status_url = f"{base_url}/api/status/{task_id}"
    last_status = "unknown"

    while time.monotonic() < deadline:
        payload = _json_request(
            status_url,
            headers=auth_headers,
            timeout_seconds=request_timeout_seconds,
            retry_attempts=request_retry_attempts,
            retry_delay_seconds=request_retry_delay_seconds,
        )
        last_status = str(payload.get("status") or "unknown").lower()
        if last_status in {"completed", "failed"}:
            return payload
        time.sleep(interval_seconds)

    raise TimeoutError(
        f"timed out waiting task status for {task_id}, last status={last_status}"
    )


def _fetch_task_status(
    *,
    base_url: str,
    task_id: str,
    auth_headers: dict[str, str],
    request_timeout_seconds: float,
    request_retry_attempts: int,
    request_retry_delay_seconds: float,
) -> dict[str, Any]:
    return _json_request(
        f"{base_url}/api/status/{task_id}",
        headers=auth_headers,
        timeout_seconds=request_timeout_seconds,
        retry_attempts=request_retry_attempts,
        retry_delay_seconds=request_retry_delay_seconds,
    )


def _poll_report(
    *,
    base_url: str,
    task_id: str,
    auth_headers: dict[str, str],
    timeout_seconds: int,
    interval_seconds: float,
    request_timeout_seconds: float,
    request_retry_attempts: int,
    request_retry_delay_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    report_url = f"{base_url}/api/report/{task_id}"
    last_error = "none"

    while time.monotonic() < deadline:
        try:
            payload = _json_request(
                report_url,
                headers=auth_headers,
                timeout_seconds=request_timeout_seconds,
                retry_attempts=request_retry_attempts,
                retry_delay_seconds=request_retry_delay_seconds,
            )
            return payload
        except urllib.error.HTTPError as exc:
            detail = _extract_http_error_detail(exc)
            if exc.code == 409:
                last_error = f"HTTP 409: {detail}"
                time.sleep(interval_seconds)
                continue
            if exc.code == 403:
                raise PermissionError(detail) from exc
            raise RuntimeError(f"load report failed: HTTP {exc.code} {detail}") from exc

    raise TimeoutError(f"timed out waiting report for {task_id}, last error={last_error}")


def _extract_report_state(
    *,
    report_payload: dict[str, Any],
    status_payload: dict[str, Any],
) -> tuple[str, str]:
    sources = report_payload.get("sources") if isinstance(report_payload, dict) else {}
    if not isinstance(sources, dict):
        sources = {}
    report_tier = str(sources.get("report_tier") or "").strip()
    blocked_reason = str(
        sources.get("analysis_blocked") or status_payload.get("blocked_reason") or ""
    ).strip()
    return report_tier, blocked_reason


def _is_report_accepted(
    *,
    report_tier: str,
    blocked_reason: str,
    required_tier: str,
    allow_blocked: bool,
) -> bool:
    tier_ok = (not required_tier) or report_tier == required_tier
    blocked_ok = allow_blocked or not blocked_reason
    return tier_ok and blocked_ok


def _wait_for_warmup_upgrade(
    *,
    base_url: str,
    task_id: str,
    auth_headers: dict[str, str],
    required_tier: str,
    allow_blocked: bool,
    timeout_seconds: int,
    interval_seconds: float,
    request_timeout_seconds: float,
    request_retry_attempts: int,
    request_retry_delay_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    started = time.monotonic()
    last_status_payload: dict[str, Any] = {}
    last_report_tier = ""
    last_blocked_reason = ""
    last_next_action = ""
    last_stage = ""
    last_error = "none"

    while time.monotonic() < deadline:
        last_status_payload = _fetch_task_status(
            base_url=base_url,
            task_id=task_id,
            auth_headers=auth_headers,
            request_timeout_seconds=request_timeout_seconds,
            request_retry_attempts=request_retry_attempts,
            request_retry_delay_seconds=request_retry_delay_seconds,
        )
        last_next_action = str(last_status_payload.get("next_action") or "").strip()
        last_stage = str(last_status_payload.get("stage") or "").strip()

        try:
            report_payload = _json_request(
                f"{base_url}/api/report/{task_id}",
                headers=auth_headers,
                timeout_seconds=request_timeout_seconds,
                retry_attempts=request_retry_attempts,
                retry_delay_seconds=request_retry_delay_seconds,
            )
        except urllib.error.HTTPError as exc:
            detail = _extract_http_error_detail(exc)
            last_error = f"HTTP {exc.code}: {detail}"
            if exc.code in {409, 429}:
                time.sleep(interval_seconds)
                continue
            if exc.code == 403:
                raise PermissionError(detail) from exc
            raise RuntimeError(f"load report failed during warmup wait: HTTP {exc.code} {detail}") from exc

        last_report_tier, last_blocked_reason = _extract_report_state(
            report_payload=report_payload,
            status_payload=last_status_payload,
        )
        if _is_report_accepted(
            report_tier=last_report_tier,
            blocked_reason=last_blocked_reason,
            required_tier=required_tier,
            allow_blocked=allow_blocked,
        ):
            waited_seconds = round(time.monotonic() - started, 2)
            return {
                "accepted": True,
                "report_tier": last_report_tier,
                "analysis_blocked": last_blocked_reason,
                "next_action": last_next_action,
                "stage": last_stage,
                "warmup_waited_seconds": waited_seconds,
            }

        if last_next_action == "manual_intervention":
            break

        time.sleep(interval_seconds)

    waited_seconds = round(time.monotonic() - started, 2)
    return {
        "accepted": False,
        "report_tier": last_report_tier,
        "analysis_blocked": last_blocked_reason,
        "next_action": last_next_action,
        "stage": last_stage,
        "warmup_waited_seconds": waited_seconds,
        "warmup_timeout": True,
        "warmup_last_error": last_error,
    }


def _login(
    *,
    base_url: str,
    email: str,
    password: str,
    request_timeout_seconds: float,
    request_retry_attempts: int,
    request_retry_delay_seconds: float,
) -> str:
    payload = _json_request(
        f"{base_url}/api/auth/login",
        {"email": email, "password": password},
        timeout_seconds=request_timeout_seconds,
        retry_attempts=request_retry_attempts,
        retry_delay_seconds=request_retry_delay_seconds,
    )
    token = str(payload.get("access_token") or "").strip()
    if not token:
        raise RuntimeError("login succeeded but access_token is missing")
    return token


def _create_analysis_task(
    *,
    base_url: str,
    product_description: str,
    topic_profile_id: str | None,
    auth_headers: dict[str, str],
    request_timeout_seconds: float,
    request_retry_attempts: int,
    request_retry_delay_seconds: float,
) -> str:
    payload: dict[str, Any] = {"product_description": product_description}
    if topic_profile_id:
        payload["topic_profile_id"] = topic_profile_id
    payload = _json_request(
        f"{base_url}/api/analyze",
        payload,
        headers=auth_headers,
        timeout_seconds=request_timeout_seconds,
        retry_attempts=request_retry_attempts,
        retry_delay_seconds=request_retry_delay_seconds,
    )
    task_id = str(payload.get("task_id") or "").strip()
    if not task_id:
        raise RuntimeError("create analysis task succeeded but task_id is missing")
    return task_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a fresh live report acceptance flow")
    parser.add_argument("--base-url", default="http://127.0.0.1:8006")
    parser.add_argument("--frontend-base-url", default="http://127.0.0.1:3006")
    parser.add_argument("--email", default="test@test.com")
    parser.add_argument("--password", default="Test123!")
    parser.add_argument("--product-description", default=DEFAULT_PRODUCT_DESCRIPTION)
    parser.add_argument("--topic-profile-id", default=None)
    parser.add_argument("--required-tier", default="A_full")
    parser.add_argument("--allow-blocked", action="store_true")
    parser.add_argument("--max-analysis-attempts", type=int, default=3)
    parser.add_argument("--analysis-retry-delay-seconds", type=float, default=2.0)
    parser.add_argument("--warmup-wait-timeout-seconds", type=int, default=420)
    parser.add_argument("--warmup-poll-interval-seconds", type=float, default=15.0)
    parser.add_argument("--status-timeout-seconds", type=int, default=210)
    parser.add_argument("--status-poll-interval-seconds", type=float, default=2.0)
    parser.add_argument("--report-timeout-seconds", type=int, default=90)
    parser.add_argument("--report-poll-interval-seconds", type=float, default=1.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--request-retry-attempts", type=int, default=3)
    parser.add_argument("--request-retry-delay-seconds", type=float, default=2.0)
    args = parser.parse_args()

    token = _login(
        base_url=args.base_url,
        email=args.email,
        password=args.password,
        request_timeout_seconds=args.request_timeout_seconds,
        request_retry_attempts=args.request_retry_attempts,
        request_retry_delay_seconds=args.request_retry_delay_seconds,
    )
    auth_headers = {"Authorization": f"Bearer {token}"}

    attempts: list[dict[str, Any]] = []

    for attempt in range(1, max(1, args.max_analysis_attempts) + 1):
        task_id = _create_analysis_task(
            base_url=args.base_url,
            product_description=args.product_description,
            topic_profile_id=args.topic_profile_id,
            auth_headers=auth_headers,
            request_timeout_seconds=args.request_timeout_seconds,
            request_retry_attempts=args.request_retry_attempts,
            request_retry_delay_seconds=args.request_retry_delay_seconds,
        )

        status_payload = _poll_status(
            base_url=args.base_url,
            task_id=task_id,
            auth_headers=auth_headers,
            timeout_seconds=args.status_timeout_seconds,
            interval_seconds=args.status_poll_interval_seconds,
            request_timeout_seconds=args.request_timeout_seconds,
            request_retry_attempts=args.request_retry_attempts,
            request_retry_delay_seconds=args.request_retry_delay_seconds,
        )
        status = str(status_payload.get("status") or "").lower()
        if status == "failed":
            attempts.append(
                {
                    "attempt": attempt,
                    "task_id": task_id,
                    "status": status,
                    "error": str(status_payload.get("error") or "analysis failed"),
                }
            )
            if attempt < args.max_analysis_attempts:
                time.sleep(args.analysis_retry_delay_seconds)
                continue
            break

        report_payload = _poll_report(
            base_url=args.base_url,
            task_id=task_id,
            auth_headers=auth_headers,
            timeout_seconds=args.report_timeout_seconds,
            interval_seconds=args.report_poll_interval_seconds,
            request_timeout_seconds=args.request_timeout_seconds,
            request_retry_attempts=args.request_retry_attempts,
            request_retry_delay_seconds=args.request_retry_delay_seconds,
        )
        report_tier, blocked_reason = _extract_report_state(
            report_payload=report_payload,
            status_payload=status_payload,
        )
        accepted = _is_report_accepted(
            report_tier=report_tier,
            blocked_reason=blocked_reason,
            required_tier=args.required_tier,
            allow_blocked=args.allow_blocked,
        )
        next_action = str(status_payload.get("next_action") or "").strip()
        stage = str(status_payload.get("stage") or "").strip()
        warmup_waited_seconds: float | None = None
        warmup_timeout = False

        if (
            not accepted
            and blocked_reason == "insufficient_samples"
            and next_action in {"wait_for_warmup", "auto_rerun_scheduled"}
            and args.warmup_wait_timeout_seconds > 0
        ):
            waited = _wait_for_warmup_upgrade(
                base_url=args.base_url,
                task_id=task_id,
                auth_headers=auth_headers,
                required_tier=args.required_tier,
                allow_blocked=args.allow_blocked,
                timeout_seconds=args.warmup_wait_timeout_seconds,
                interval_seconds=args.warmup_poll_interval_seconds,
                request_timeout_seconds=args.request_timeout_seconds,
                request_retry_attempts=args.request_retry_attempts,
                request_retry_delay_seconds=args.request_retry_delay_seconds,
            )
            accepted = bool(waited.get("accepted"))
            report_tier = str(waited.get("report_tier") or report_tier)
            blocked_reason = str(waited.get("analysis_blocked") or blocked_reason)
            next_action = str(waited.get("next_action") or next_action)
            stage = str(waited.get("stage") or stage)
            warmup_waited_seconds = (
                float(waited["warmup_waited_seconds"])
                if waited.get("warmup_waited_seconds") is not None
                else None
            )
            warmup_timeout = bool(waited.get("warmup_timeout") or False)

        attempt_payload = {
            "attempt": attempt,
            "task_id": task_id,
            "status": status,
            "report_tier": report_tier,
            "analysis_blocked": blocked_reason,
            "stage": stage,
            "next_action": next_action,
            "data_source": report_payload.get("data_source"),
            "result_url": f"{args.frontend_base_url}/report/{task_id}",
            "warmup_waited_seconds": warmup_waited_seconds,
            "warmup_timeout": warmup_timeout,
            "accepted": accepted,
        }
        attempts.append(attempt_payload)

        if accepted:
            print(
                json.dumps(
                    {
                        "accepted": True,
                        "email": args.email,
                        "topic_profile_id": args.topic_profile_id,
                        "required_tier": args.required_tier,
                        **attempt_payload,
                        "attempts": attempts,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

        if attempt < args.max_analysis_attempts:
            time.sleep(args.analysis_retry_delay_seconds)

    failure_payload = {
        "accepted": False,
        "email": args.email,
        "topic_profile_id": args.topic_profile_id,
        "required_tier": args.required_tier,
        "allow_blocked": args.allow_blocked,
        "attempts": attempts,
    }
    print(json.dumps(failure_payload, ensure_ascii=False, indent=2), file=sys.stderr)
    raise RuntimeError("live report acceptance failed after max attempts")


if __name__ == "__main__":
    try:
        main()
    except PermissionError as exc:  # pragma: no cover - acceptance utility
        print(f"run_live_report_acceptance failed: {exc}", file=sys.stderr)
        raise
    except Exception as exc:  # pragma: no cover - acceptance utility
        print(f"run_live_report_acceptance failed: {exc}", file=sys.stderr)
        raise
