"""
Day 10 Admin end-to-end validation script.

Source of requirements:
- reports/DAY10 plan (screenshot instructions)
- docs/PRD/PRD-07-Admin后台.md (Admin dashboard KPIs & access control)
- docs/PRD/PRD-06-用户认证.md (JWT +租户隔离)
- docs/PRD/PRD-08-端到端测试规范.md (端到端测试流程)

This script validates that:
1. Admin allowlist (ADMIN_EMAILS) is configured and accessible.
2. Admin tokens can reach `/api/admin/dashboard/stats`, `/tasks/recent`, `/users/active`.
3. Recently created analysis tasks appear in the Admin views.

Prerequisites (must be satisfied before running):
- Redis, Celery worker, backend API, and analysis pipeline are running.
- `ADMIN_EMAILS` includes the admin email used for the test.
- Optionally set `ADMIN_E2E_PASSWORD` if the admin account already exists with a known password.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Tuple

import httpx


BASE_URL = os.getenv("ADMIN_E2E_BASE_URL", "http://localhost:8006")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("ADMIN_E2E_REQUEST_TIMEOUT", "300"))
TASK_TIMEOUT_SECONDS = int(os.getenv("ADMIN_E2E_TASK_TIMEOUT", "300"))
POLL_INTERVAL_SECONDS = float(os.getenv("ADMIN_E2E_POLL_INTERVAL", "3"))

DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_E2E_PASSWORD", "TestAdmin123")
DEFAULT_USER_PASSWORD = os.getenv("ADMIN_E2E_USER_PASSWORD", "TestPass123")


class AdminE2EError(RuntimeError):
    """Raised when the admin end-to-end validation fails."""


def _select_admin_email() -> str:
    raw = os.getenv("ADMIN_EMAILS", "").strip()
    if not raw:
        raise AdminE2EError(
            "ADMIN_EMAILS is not configured. "
            "Set ADMIN_EMAILS (e.g. export ADMIN_EMAILS=admin-e2e@example.com) before running this script."
        )

    for email in raw.split(","):
        candidate = email.strip().lower()
        if candidate:
            return candidate

    raise AdminE2EError(
        "ADMIN_EMAILS is configured but contains no valid email entries. "
        "Ensure ADMIN_EMAILS includes at least one non-empty email."
    )


async def _assert_backend_ready(client: httpx.AsyncClient) -> None:
    """Validate the backend is reachable before running the heavy flow."""
    healthz = f"{BASE_URL}/api/healthz"
    response = await client.get(healthz, timeout=10.0)
    if response.status_code != httpx.codes.OK:
        raise AdminE2EError(f"Backend health check failed ({healthz} -> {response.status_code})")


async def _register_user(
    client: httpx.AsyncClient,
    email: str,
    password: str,
) -> tuple[str, dict[str, object]]:
    """Attempt to register a user and return access token and response body."""
    register_url = f"{BASE_URL}/api/auth/register"
    payload = {"email": email, "password": password}
    response = await client.post(register_url, json=payload, timeout=30.0)
    if response.status_code == httpx.codes.CREATED:
        body = response.json()
        return body["access_token"], body

    if response.status_code == httpx.codes.CONFLICT:
        # User already exists; caller should attempt login separately.
        raise AdminE2EError("User already exists")

    detail = response.text
    raise AdminE2EError(f"Register failed for {email}: {response.status_code} {detail}")


async def _login_user(
    client: httpx.AsyncClient,
    email: str,
    password: str,
) -> tuple[str, dict[str, object]]:
    login_url = f"{BASE_URL}/api/auth/login"
    payload = {"email": email, "password": password}
    response = await client.post(login_url, json=payload, timeout=30.0)
    if response.status_code != httpx.codes.OK:
        raise AdminE2EError(
            f"Login failed for {email}: {response.status_code} {response.text}. "
            "For admin accounts, ensure ADMIN_E2E_PASSWORD matches the stored password."
        )
    body = response.json()
    return body["access_token"], body


async def _ensure_account(
    client: httpx.AsyncClient,
    email: str,
    password: str,
) -> Tuple[str, dict[str, object], bool]:
    """
    Return (token, auth_payload, is_newly_created).

    If the account already exists, falls back to login using the provided password.
    """
    try:
        token, payload = await _register_user(client, email, password)
        return token, payload, True
    except AdminE2EError as exc:
        if "already exists" in str(exc):
            token, payload = await _login_user(client, email, password)
            return token, payload, False
        raise


async def _create_analysis_task(
    client: httpx.AsyncClient,
    token: str,
    description: str,
) -> str:
    analyze_url = f"{BASE_URL}/api/analyze"
    response = await client.post(
        analyze_url,
        headers={"Authorization": f"Bearer {token}"},
        json={"product_description": description},
        timeout=30.0,
    )
    # Accept both 200 OK and 201 Created
    if response.status_code not in (httpx.codes.OK, httpx.codes.CREATED):
        raise AdminE2EError(
            f"Failed to create analysis task: {response.status_code} {response.text}"
        )
    body = response.json()
    task_id = body["task_id"]
    print(f"   [PASS] Created analysis task {task_id} for '{description}'")
    return task_id


async def _wait_for_completion(
    client: httpx.AsyncClient,
    token: str,
    task_id: str,
) -> None:
    status_url = f"{BASE_URL}/api/status/{task_id}"
    start = time.time()

    while True:
        response = await client.get(
            status_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )
        if response.status_code != httpx.codes.OK:
            raise AdminE2EError(
                f"Status check failed for {task_id}: {response.status_code} {response.text}"
            )

        payload = response.json()
        status = payload.get("status")
        progress = payload.get("progress")
        elapsed = time.time() - start
        print(f"      status={status} progress={progress} elapsed={elapsed:.1f}s")

        if status == "completed":
            print(f"   [PASS] Task {task_id} completed in {elapsed:.1f}s")
            return
        if status == "failed":
            raise AdminE2EError(f"Task {task_id} failed: {payload.get('error')}")
        if elapsed > TASK_TIMEOUT_SECONDS:
            raise AdminE2EError(
                f"Task {task_id} timed out after {elapsed:.1f}s (limit {TASK_TIMEOUT_SECONDS}s)"
            )

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _fetch_admin_endpoint(
    client: httpx.AsyncClient,
    token: str,
    path: str,
) -> dict[str, object]:
    url = f"{BASE_URL}{path}"
    response = await client.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    if response.status_code != httpx.codes.OK:
        raise AdminE2EError(
            f"Admin endpoint {path} failed: {response.status_code} {response.text}"
        )
    body = response.json()
    if body.get("code") != 0:
        raise AdminE2EError(f"Admin endpoint {path} returned non-zero code: {body}")
    return body


async def run() -> None:
    admin_email = _select_admin_email()
    regular_email = f"admin-e2e-user-{int(time.time())}@example.com"

    print("============================================================")
    print("Admin E2E Validation")
    print("============================================================")
    print(f"[INFO] Base URL: {BASE_URL}")
    print(f"[INFO] Admin email: {admin_email}")
    print(f"[INFO] Regular user email: {regular_email}")
    print("[INFO] Ensure Redis, Celery worker, and backend API are running.")

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        await _assert_backend_ready(client)

        print("\n[STEP 1] Ensure admin account exists and obtain token")
        admin_token, admin_payload, admin_created = await _ensure_account(
            client, admin_email, DEFAULT_ADMIN_PASSWORD
        )
        if admin_created:
            print(f"   [PASS] Admin account created: {admin_payload['user']['email']}")
        else:
            print(f"   [PASS] Admin account reused: {admin_payload['user']['email']}")

        print("\n[STEP 2] Create supporting regular user")
        user_token, user_payload, user_created = await _ensure_account(
            client, regular_email, DEFAULT_USER_PASSWORD
        )
        status_flag = "created" if user_created else "reused"
        print(f"   [PASS] Regular account {status_flag}: {user_payload['user']['email']}")

        print("\n[STEP 3] Trigger analysis tasks")
        admin_task = await _create_analysis_task(
            client,
            admin_token,
            "Admin dashboard validation task (admin)",
        )
        user_task = await _create_analysis_task(
            client,
            user_token,
            "Admin dashboard validation task (user)",
        )

        print("   [INFO] Waiting for tasks to complete ...")
        await _wait_for_completion(client, admin_token, admin_task)
        await _wait_for_completion(client, user_token, user_task)

        print("\n[STEP 4] Validate Admin endpoints")
        dashboard = await _fetch_admin_endpoint(client, admin_token, "/api/admin/dashboard/stats")
        recent = await _fetch_admin_endpoint(client, admin_token, "/api/admin/tasks/recent")
        active = await _fetch_admin_endpoint(client, admin_token, "/api/admin/users/active")

        stats = dashboard["data"]
        print("   [PASS] Dashboard metrics retrieved")
        for field in ("total_users", "total_tasks", "tasks_today", "tasks_completed_today"):
            if field not in stats:
                raise AdminE2EError(f"Dashboard missing field: {field}")
        print(f"      total_users={stats['total_users']}  total_tasks={stats['total_tasks']}")
        print(f"      tasks_today={stats['tasks_today']}  completed_today={stats['tasks_completed_today']}")
        print(f"      avg_processing_time={stats.get('avg_processing_time')}  cache_hit_rate={stats.get('cache_hit_rate')}")
        print(f"      active_workers={stats.get('active_workers')}")

        recent_items = recent["data"]["items"]
        recent_ids = {item["task_id"] for item in recent_items}
        if admin_task not in recent_ids or user_task not in recent_ids:
            raise AdminE2EError(
                "Recent tasks endpoint did not include the newly created tasks. "
                f"Found tasks: {recent_ids}"
            )
        print(f"   [PASS] Recent tasks include admin task {admin_task} and user task {user_task}")

        active_items = active["data"]["items"]
        active_map = {item["email"]: item for item in active_items}
        if admin_email not in active_map or regular_email not in active_map:
            raise AdminE2EError(
                "Active users endpoint missing expected users. "
                f"Current map keys: {list(active_map.keys())}"
            )
        print(
            f"   [PASS] Active users list includes admin ({admin_email}) "
            f"and regular user ({regular_email})"
        )
        print(
            f"      admin tasks_last_7_days={active_map[admin_email]['tasks_last_7_days']} "
            f"regular tasks_last_7_days={active_map[regular_email]['tasks_last_7_days']}"
        )

        print("\n[RESULT] ✅ Admin end-to-end validation passed.")


def main() -> None:
    try:
        asyncio.run(run())
    except AdminE2EError as exc:
        print(f"\n[RESULT] ❌ Admin end-to-end validation failed: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:  # pragma: no cover - user cancellation
        print("\n[RESULT] ❌ Aborted by user", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
