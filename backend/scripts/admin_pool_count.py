from __future__ import annotations

"""
Admin helper: login and fetch community pool count.

Env vars:
  BACKEND_URL      (default: http://localhost:8006)
  ADMIN_EMAIL      (required)
  ADMIN_PASSWORD   (required)

Writes a snapshot JSON to reports/local-acceptance/ when run from repo root via Makefile.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import httpx


async def main() -> int:
    base = os.getenv("BACKEND_URL", "http://localhost:8006").rstrip("/")
    email = os.getenv("ADMIN_EMAIL", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    if not email or not password:
        print("Missing ADMIN_EMAIL or ADMIN_PASSWORD", file=sys.stderr)
        return 2

    async with httpx.AsyncClient() as client:
        login = await client.post(
            f"{base}/api/auth/login",
            json={"email": email, "password": password},
            timeout=20.0,
        )
        if login.status_code != 200:
            print(f"Login failed: {login.status_code} {login.text}", file=sys.stderr)
            return 3
        token = login.json().get("access_token")

        resp = await client.get(
            f"{base}/api/admin/communities/pool",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        if resp.status_code != 200:
            print(
                f"Pool fetch failed: {resp.status_code} {resp.text}", file=sys.stderr
            )
            return 4

        payload = resp.json()
        data = payload.get("data", {})
        total = int(data.get("total", 0))

        # Save snapshot relative to repo root if possible
        out = Path(__file__).resolve().parents[2] / "reports" / "local-acceptance"
        out.mkdir(parents=True, exist_ok=True)
        snap = out / f"admin-pool-snapshot-{int(time.time())}.json"
        snap.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"TOTAL {total}")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

