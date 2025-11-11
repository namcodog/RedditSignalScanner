#!/usr/bin/env python3
from __future__ import annotations

"""
Quick diagnostic: print competitor_layers_summary for a given task_id as JSON.

Env:
  BACKEND_URL (default: http://localhost:8006)
  ACCESS_TOKEN (JWT; optional — if missing, will try EMAIL/PASSWORD to login or register)
  EMAIL, PASSWORD (optional)

Usage:
  python -u backend/scripts/competitor_smoke.py --task TASK_ID > reports/local-acceptance/competitor-layers-<task>.json
"""

import argparse
import json
import os
from pathlib import Path
import uuid

import httpx


async def _login_or_register(client: httpx.AsyncClient, base: str, email: str | None, password: str | None) -> str:
    if not email:
        email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
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
    ap = argparse.ArgumentParser(description="Competitor layers smoke output")
    ap.add_argument("--task", required=True, help="Task ID")
    ap.add_argument("--out", type=Path, help="Output JSON path", default=None)
    args = ap.parse_args()

    base = os.getenv("BACKEND_URL", "http://localhost:8006").rstrip("/")
    token = os.getenv("ACCESS_TOKEN")
    async with httpx.AsyncClient() as client:
        if not token:
            try:
                token = await _login_or_register(client, base, os.getenv("EMAIL"), os.getenv("PASSWORD"))
            except Exception:
                token = None
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = await client.get(f"{base}/api/report/{args.task}", headers=headers, timeout=60.0)
        r.raise_for_status()
        data = r.json() or {}
        layers = (data.get("report") or {}).get("competitor_layers_summary") or []
        payload = {"task_id": args.task, "competitor_layers_summary": layers}
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8")
        print(text)
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))

