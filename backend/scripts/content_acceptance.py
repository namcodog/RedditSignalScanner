#!/usr/bin/env python3
from __future__ import annotations

"""
Content acceptance checker for report quality (Spec 008 - P0/P2 seed).

Env vars:
  BACKEND_URL (default: http://localhost:8006)
  EMAIL, PASSWORD (optional; if omitted, script registers a unique account)
  TASK_ID (optional; if omitted, script will create a new task with a default description)

Outputs a JSON summary to reports/local-acceptance/content-acceptance-*.json and
returns a non-zero exit code if quality checks fail.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict

import httpx


DEFAULT_DESC = "AI-powered weekly executive updates for remote teams"


async def _login_or_register(client: httpx.AsyncClient, base: str, email: str | None, password: str | None) -> str:
    if not email:
        email = f"content-accept-{uuid.uuid4().hex[:8]}@example.com"
    if not password:
        password = "testpass123"
    r = await client.post(f"{base}/api/auth/register", json={"email": email, "password": password, "membership_level": "pro"}, timeout=30.0)
    if r.status_code not in (200, 201):
        r = await client.post(f"{base}/api/auth/login", json={"email": email, "password": password}, timeout=30.0)
        r.raise_for_status()
    data = r.json()
    return data["access_token"]


async def _create_task(client: httpx.AsyncClient, base: str, token: str, description: str) -> str:
    r = await client.post(f"{base}/api/analyze", headers={"Authorization": f"Bearer {token}"}, json={"product_description": description}, timeout=30.0)
    r.raise_for_status()
    return r.json()["task_id"]


async def _wait_completion(client: httpx.AsyncClient, base: str, token: str, task_id: str, timeout_s: int = 90) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        r = await client.get(f"{base}/api/status/{task_id}", headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
        if r.status_code == 200 and r.json().get("status") == "completed":
            return
        await asyncio.sleep(3)
    raise RuntimeError("task not completed within timeout")


def _check_quality(report: Dict[str, Any]) -> Dict[str, Any]:
    # P2: 扩展质量门禁：
    # - 统计一致性
    # - 行动项数量与证据密度（每条≥2个可点击URL）
    # - Top 社区存在
    # - 洞察丰富度（痛点/机会的最小数量）
    stats = report.get("stats", {})
    overview = report.get("overview", {})
    content = report.get("report", {})

    pos = int(stats.get("positive_mentions", 0) or 0)
    neg = int(stats.get("negative_mentions", 0) or 0)
    neu = int(stats.get("neutral_mentions", 0) or 0)
    total = int(stats.get("total_mentions", 0) or 0)
    stats_consistent = (pos + neg + neu) == total and total >= 0

    ai = content.get("action_items") or []
    action_items_ok = len(ai) >= 1
    # 证据密度（每条≥2个可点击URL）
    evidence_ok = True
    if ai:
        for item in ai:
            ev = item.get("evidence_chain") or []
            url_count = sum(1 for e in ev if (e or {}).get("url"))
            if url_count < 2:
                evidence_ok = False
                break

    top = (overview.get("top_communities") or [])
    top_ok = len(top) >= 1

    # 洞察丰富度（痛点≥3 或 机会≥2）
    pains = content.get("pain_points") or []
    opps = content.get("opportunities") or []
    richness_ok = (len(pains) >= 3) or (len(opps) >= 2)

    score = 100
    if not stats_consistent:
        score -= 30
    if not action_items_ok:
        score -= 30
    if not top_ok:
        score -= 20
    if not evidence_ok:
        score -= 20
    if not richness_ok:
        score -= 10
    passed = score >= 70

    return {
        "passed": passed,
        "score": score,
        "stats_consistent": stats_consistent,
        "action_items_count": len(ai),
        "evidence_ok": evidence_ok,
        "richness_ok": richness_ok,
        "top_communities_count": len(top),
    }


async def main() -> int:
    base = os.getenv("BACKEND_URL", "http://localhost:8006").rstrip("/")
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    task_id = os.getenv("TASK_ID")

    async with httpx.AsyncClient() as client:
        try:
            token = await _login_or_register(client, base, email, password)
            headers = {"Authorization": f"Bearer {token}"}

            if not task_id:
                task_id = await _create_task(client, base, token, DEFAULT_DESC)
                await _wait_completion(client, base, token, task_id)

            rep = await client.get(f"{base}/api/report/{task_id}", headers=headers, timeout=60.0)
            rep.raise_for_status()
            report = rep.json()

            result = _check_quality(report)
        except Exception as exc:
            result = {"passed": False, "error": str(exc), "score": 0}

    out = Path("reports/local-acceptance")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"content-acceptance-{int(time.time())}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
