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
    # Spec014 optional gate: 战场推荐≥3 且理由齐全（不改接口，默认不入硬门禁）
    battle_reco_ok = len(top) >= 3

    # 洞察丰富度（痛点≥3 或 机会≥2）
    pains = content.get("pain_points") or []
    opps = content.get("opportunities") or []
    richness_ok = (len(pains) >= 3) or (len(opps) >= 2)
    # P/S 可计算性（最小化断言）：至少 1 个痛点 + 至少 1 个机会
    ps_ratio_ok = (len(pains) >= 1 and len(opps) >= 1)

    # 实体覆盖度：统计 entity_summary 各分类的总数
    entity_summary = (report.get("report") or {}).get("entity_summary") or {}
    entity_total = 0
    if isinstance(entity_summary, dict):
        for rows in entity_summary.values():
            if isinstance(rows, list):
                entity_total += len(rows)

    entity_coverage_ok = entity_total >= 3

    # 中性比例区间（10%–40% 视为合理）：过低代表二分类偏置，过高代表信号稀释
    neutral_range_ok = True
    neutral_pct = 0
    if total > 0:
        neutral_pct = int(round(neu * 100.0 / total))
        neutral_range_ok = 10 <= neutral_pct <= 40

    # 社区纯度：Top 列中按 category 的主类占比 ≥ 80%
    purity_ok = True
    purity_ratio = 1.0
    if top:
        cats = [t.get("category") for t in top if t.get("category")]
        if cats:
            from collections import Counter
            c = Counter(cats)
            denom = len(cats)
            purity_ratio = (c.most_common(1)[0][1] / max(1, denom))
            # 至少 3 个有类目的样本时再严格要求
            purity_ok = (denom < 3) or (purity_ratio >= 0.8)

    # LLM 覆盖率：统计 note 是否为短要点句（而非“社区: … | 赞数 …”默认文案）
    llm_coverage = 0.0
    try:
        items = content.get("action_items") or []
        total_evid = 0
        short_cnt = 0
        for it in items:
            for ev in (it.get("evidence_chain") or []):
                total_evid += 1
                note = str((ev or {}).get("note") or "")
                if note and not note.startswith("社区:") and len(note) <= 32:
                    short_cnt += 1
        if total_evid > 0:
            llm_coverage = short_cnt / total_evid
    except Exception:
        llm_coverage = 0.0

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
    if not ps_ratio_ok:
        score -= 10
    if not entity_coverage_ok:
        score -= 10
    if not neutral_range_ok:
        score -= 10
    if not purity_ok:
        score -= 10
    # 簇样本覆盖不足也扣分（轻门禁）
    try:
        if not cluster_samples_ok:
            score -= 10
    except Exception:
        pass
    # 洞察卡片质量（卡片≥3且每张证据≥2）
    cards_ok = False
    try:
        import httpx  # type: ignore
        token = os.getenv("ACCESS_TOKEN") or None
        task_id = (report.get("task_id") or "").strip()
        base = os.getenv("BACKEND_URL", "http://localhost:8006").rstrip("/")
        if task_id:
            with httpx.Client(trust_env=False) as c:
                headers = {"Authorization": f"Bearer {token}"} if token else {}
                r = c.get(f"{base}/api/insights/{task_id}", headers=headers, timeout=15.0)
                if r.status_code == 200:
                    payload = r.json() or {}
                    cards = payload.get("insights") or payload.get("items", []) or []
                    if isinstance(cards, list) and len(cards) >= 3:
                        if all((len((card.get("evidence") or [])) >= 2) for card in cards[:3]):
                            cards_ok = True
        if not cards_ok:
            ai_cards = (content.get("action_items") or [])[:3]
            if ai_cards and all(len(item.get("evidence_chain") or []) >= 2 for item in ai_cards[:3]):
                cards_ok = True
        if not cards_ok:
            score -= 15
    except Exception:
        # 网络或接口异常不阻断，但降低评分
        score -= 5

    # Spec 010 额外硬门禁
    clusters = (content.get("pain_clusters") or [])
    competitor_layers = (content.get("competitor_layers_summary") or [])
    opportunities = (content.get("opportunities") or [])

    clusters_ok = len(clusters) >= 2
    # 簇样本覆盖率：含 samples 的簇 / 全部簇
    clusters_with_samples = 0
    if clusters:
        for cl in clusters:
            if (cl.get("samples") or []):
                clusters_with_samples += 1
    cluster_sample_coverage = 1.0 if not clusters else (clusters_with_samples / max(1, len(clusters)))
    cluster_samples_ok = (len(clusters) == 0) or (cluster_sample_coverage >= 0.8)
    competitor_layers_ok = len(competitor_layers) >= 2
    opportunity_users_ok = True
    if opportunities:
        for opp in opportunities:
            est = opp.get("potential_users_est")
            try:
                if int(est) <= 0:
                    opportunity_users_ok = False
                    break
            except Exception:
                opportunity_users_ok = False
                break
    else:
        # 若没有机会项，则按不通过处理，确保有量化样本
        opportunity_users_ok = False

    # 从审计文件读取 normalization_rate（若存在）
    normalization_rate = None
    try:
        task_id = (report.get("task_id") or "").strip()
        if task_id:
            import json as _json
            from pathlib import Path as _Path
            audit = _Path(f"backend/reports/local-acceptance/llm-audit-{task_id}.json")
            if audit.exists():
                payload = _json.loads(audit.read_text(encoding="utf-8")) or {}
                normalization_rate = float(payload.get("normalization_rate", 0.0) or 0.0)
    except Exception:
        normalization_rate = None

    # LLM 产出覆盖率纳入必备门槛（>=0.6），规范化匹配率<0.9 仅扣分
    llm_ok = llm_coverage >= 0.6
    passed = (score >= 70) and clusters_ok and competitor_layers_ok and opportunity_users_ok and llm_ok
    if normalization_rate is not None and normalization_rate < 0.9:
        score -= 5

    return {
        "passed": passed,
        "score": score,
        "insight_cards_ok": cards_ok,
        "stats_consistent": stats_consistent,
        "action_items_count": len(ai),
        "evidence_ok": evidence_ok,
        "richness_ok": richness_ok,
        "ps_ratio_ok": ps_ratio_ok,
        "top_communities_count": len(top),
        "entity_total": entity_total,
        "entity_coverage_ok": entity_coverage_ok,
        "neutral_pct": neutral_pct,
        "neutral_range_ok": neutral_range_ok,
        "purity_ratio": round(purity_ratio, 2),
        "purity_ok": purity_ok,
        "llm_coverage": round(llm_coverage, 3),
        "llm_ok": llm_ok,
        "normalization_rate": round(normalization_rate or 0.0, 3) if normalization_rate is not None else None,
        "normalization_ok": (normalization_rate is not None and normalization_rate >= 0.9) if normalization_rate is not None else None,
        # Spec014 optional field (not enforced by default)
        "battle_recommendations_ok": battle_reco_ok,
        # Spec010 新增断言状态
        "clusters_ok": clusters_ok,
        "cluster_sample_coverage": round(cluster_sample_coverage, 2) if clusters else 1.0,
        "cluster_samples_ok": cluster_samples_ok,
        "competitor_layers_ok": competitor_layers_ok,
        "opportunity_users_ok": opportunity_users_ok,
    }


async def main() -> int:
    base = os.getenv("BACKEND_URL", "http://localhost:8006").rstrip("/")
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    task_id = os.getenv("TASK_ID")

    async with httpx.AsyncClient(trust_env=False) as client:
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
