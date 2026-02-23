#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import uuid
import httpx


async def _login_or_register(client: httpx.AsyncClient, base: str, email: str | None, password: str | None) -> str:
    if not email:
        email = f"report-dl-{uuid.uuid4().hex[:8]}@example.com"
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
    ap = argparse.ArgumentParser(description="Download report in specified format")
    ap.add_argument("--task", required=True)
    ap.add_argument("--format", choices=["md", "pdf", "json"], default="md")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    base = os.getenv("BACKEND_URL", "http://localhost:8006").rstrip("/")
    token = os.getenv("ACCESS_TOKEN")
    async with httpx.AsyncClient() as client:
        if not token:
            token = await _login_or_register(client, base, os.getenv("EMAIL"), os.getenv("PASSWORD"))
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.get(f"{base}/api/report/{args.task}/download", params={"format": args.format}, headers=headers, timeout=60.0)
        r.raise_for_status()
        content = r.content
        if args.out is None:
            ext = "md" if args.format == "md" else ("pdf" if args.format == "pdf" else "json")
            args.out = Path(f"backend/reports/local-acceptance/report-{args.task}.{ext}")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(content)
        print(f"Report saved to {args.out}")
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))

