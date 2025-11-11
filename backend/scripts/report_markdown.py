#!/usr/bin/env python3
from __future__ import annotations

"""
Fetch controlled Markdown report for a given task id and save to file.

Env:
  BACKEND_URL (default: http://localhost:8006)
  ACCESS_TOKEN (optional); or provide EMAIL/PASSWORD to login/register

Usage:
  python -u backend/scripts/report_markdown.py --task <TASK_ID> --out reports/local-acceptance/controlled_report.md
"""

import argparse
from pathlib import Path
import os
import uuid
import httpx


async def _login_or_register(client: httpx.AsyncClient, base: str, email: str | None, password: str | None) -> str:
    if not email:
        email = f"report-md-{uuid.uuid4().hex[:8]}@example.com"
    if not password:
        password = "testpass123"
    r = await client.post(f"{base}/api/auth/login", json={"email": email, "password": password}, timeout=20.0)
    if r.status_code == 200:
        return r.json()["access_token"]
    r = await client.post(
        f"{base}/api/auth/register",
        json={"email": email, "password": password, "membership_level": "pro"},
        timeout=20.0,
    )
    r.raise_for_status()
    return r.json()["access_token"]


async def main() -> int:
    ap = argparse.ArgumentParser(description="Download Markdown report")
    ap.add_argument("--task", required=True)
    ap.add_argument("--out", type=Path, default=Path("backend/reports/local-acceptance/controlled_report.md"))
    args = ap.parse_args()

    base = os.getenv("BACKEND_URL", "http://localhost:8006").rstrip("/")
    token = os.getenv("ACCESS_TOKEN")
    async with httpx.AsyncClient() as client:
        if not token:
            token = await _login_or_register(client, base, os.getenv("EMAIL"), os.getenv("PASSWORD"))
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.get(f"{base}/api/report/{args.task}/download", params={"format": "md"}, headers=headers, timeout=60.0)
        r.raise_for_status()
        content = r.content
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(content)
        print(f"Report saved to {args.out}")
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))

