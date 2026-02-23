#!/usr/bin/env python3
"""
Phase106 - 真人黄金路径“生产演练矩阵”

目标（大白话）：
1) 走你们的黄金链路：POST /api/analyze → 轮询 /api/status → GET /api/report
2) 同时用 Admin 账本接口抓 sources/facts_snapshot，能复盘“为什么是这个 tier / 卡点是什么 / 补量做了什么”
3) 把演练过程与结果写成可机器复核的输出（stdout + 可选 JSON 文件）

使用方式（建议）：
  export PHASE106_TOKEN="你的 JWT"
  export ADMIN_EMAILS="把当前 token 的 email 加进来"
  python scripts/phase106_rehearsal_matrix.py --config scripts/phase106_rehearsal_matrix.sample.json

注意：
- 这不是“单元测试”，它需要你本地服务/worker/redis 真的跑起来。
- 你可以先跑一条 scenario 看通，再开全矩阵。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


def _now_ms() -> int:
    return int(time.time() * 1000)


def _http_json(
    *,
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> tuple[int, dict[str, Any] | None, str]:
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if payload is not None:
        raw = json.dumps(payload).encode("utf-8")
        data = raw
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = int(getattr(resp, "status", 200))
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = int(getattr(exc, "code", 0) or 0)
        body = exc.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return 0, None, f"request failed: {exc}"

    if not body:
        return status, None, ""
    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            return status, parsed, body
        return status, None, body
    except json.JSONDecodeError:
        return status, None, body


@dataclass
class Scenario:
    name: str
    product_description: str
    topic_profile_id: str | None = None
    mode: str | None = None
    audit_level: str | None = None
    max_wait_seconds: int = 600
    expect_tier_in: list[str] | None = None
    require_comments: bool = False
    stop_on_next_action_in: list[str] | None = None


def _load_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _require_str(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"config.{key} must be a non-empty string")
    return value.strip()


def _optional_str(obj: dict[str, Any], key: str) -> str | None:
    value = obj.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"config.{key} must be a string")
    value = value.strip()
    return value or None


def _parse_scenarios(cfg: dict[str, Any]) -> list[Scenario]:
    raw = cfg.get("scenarios")
    if not isinstance(raw, list) or not raw:
        raise ValueError("config.scenarios must be a non-empty list")

    scenarios: list[Scenario] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = _require_str(item, "name")
        desc = _require_str(item, "product_description")
        expect = item.get("expect_tier_in")
        expect_list = None
        if isinstance(expect, list):
            expect_list = [str(x) for x in expect if str(x).strip()]
        require_comments = bool(item.get("require_comments") or False)
        stop_actions = item.get("stop_on_next_action_in")
        stop_list = None
        if isinstance(stop_actions, list):
            stop_list = [str(x).strip() for x in stop_actions if str(x).strip()]
        scenarios.append(
            Scenario(
                name=name,
                product_description=desc,
                topic_profile_id=_optional_str(item, "topic_profile_id"),
                mode=_optional_str(item, "mode"),
                audit_level=_optional_str(item, "audit_level"),
                max_wait_seconds=int(item.get("max_wait_seconds", 600) or 600),
                expect_tier_in=expect_list,
                require_comments=require_comments,
                stop_on_next_action_in=stop_list,
            )
        )
    if not scenarios:
        raise ValueError("No valid scenarios found in config.scenarios")
    return scenarios


def _poll_status(
    *,
    base_url: str,
    token: str,
    task_id: str,
    max_wait_seconds: int,
    stop_on_next_action_in: list[str] | None = None,
) -> dict[str, Any]:
    url = f"{base_url}/status/{task_id}"
    start = time.time()
    last_sig = ""
    while True:
        code, obj, raw = _http_json(method="GET", url=url, token=token)
        if code == 0:
            raise RuntimeError(raw)
        if code != 200 or obj is None:
            raise RuntimeError(f"status poll failed: http={code}, body={raw[:200]}")

        status = str(obj.get("status") or "").strip()
        stage = str(obj.get("stage") or "").strip() or None
        blocked_reason = str(obj.get("blocked_reason") or "").strip() or None
        next_action = str(obj.get("next_action") or "").strip() or None
        sig = f"{status}|{stage}|{blocked_reason}|{next_action}|{obj.get('progress')}"
        if sig != last_sig:
            last_sig = sig
            print(
                f"[status] {task_id} status={status} stage={stage} blocked={blocked_reason} next={next_action} progress={obj.get('progress')}",
                flush=True,
            )

        if status == "failed":
            return obj
        if status == "completed":
            # 注意：Phase105/106 设计里，warmup/auto_rerun 期间也可能保持 completed（为了 /api/report 可读）。
            # 只有当 stage=done（或明确需要人工介入）才算“真正终态”。
            if stage in {"warmup", "auto_rerun"}:
                if stop_on_next_action_in and next_action in set(stop_on_next_action_in):
                    return obj
                if next_action in {"manual_intervention", "manual_retry"}:
                    return obj
            else:
                return obj

        if time.time() - start > max_wait_seconds:
            raise TimeoutError(f"timeout waiting for task {task_id} after {max_wait_seconds}s")
        time.sleep(2)


def _fetch_admin_ledger(
    *,
    base_url: str,
    token: str,
    task_id: str,
) -> dict[str, Any] | None:
    # include_package=true：拿到 facts_snapshot.v2_package，才能复盘“评论证据链/口径一致性”
    url = f"{base_url}/admin/tasks/{task_id}/ledger?include_package=true"
    code, obj, raw = _http_json(method="GET", url=url, token=token)
    if code == 403:
        print("[ledger] 403 (not admin / ADMIN_EMAILS not configured)", flush=True)
        return None
    if code != 200 or obj is None:
        print(f"[ledger] failed http={code} body={raw[:200]}", flush=True)
        return None
    return obj


def _fetch_task_sources_ledger(
    *,
    base_url: str,
    token: str,
    task_id: str,
) -> dict[str, Any] | None:
    url = f"{base_url}/tasks/{task_id}/sources"
    code, obj, raw = _http_json(method="GET", url=url, token=token)
    if code == 403:
        print("[sources] 403 (not owner?)", flush=True)
        return None
    if code != 200 or obj is None:
        print(f"[sources] failed http={code} body={raw[:200]}", flush=True)
        return None
    return obj


def _fetch_report(
    *,
    base_url: str,
    token: str,
    task_id: str,
) -> tuple[int, str]:
    url = f"{base_url}/report/{task_id}"
    code, _obj, raw = _http_json(method="GET", url=url, token=token)
    return code, raw


def _extract_tier_from_ledger(ledger: dict[str, Any] | None) -> str:
    if not ledger:
        return ""
    analysis = ledger.get("analysis")
    if isinstance(analysis, dict):
        sources = analysis.get("sources")
        if isinstance(sources, dict):
            tier = sources.get("report_tier")
            if isinstance(tier, str) and tier.strip():
                return tier.strip()
    facts = ledger.get("facts_snapshot")
    if isinstance(facts, dict):
        tier = facts.get("tier")
        if isinstance(tier, str) and tier.strip():
            return tier.strip()
    return ""


def _extract_tier_from_sources_ledger(payload: dict[str, Any] | None) -> str:
    if not payload:
        return ""
    sources = payload.get("sources")
    if isinstance(sources, dict):
        tier = sources.get("report_tier")
        if isinstance(tier, str) and tier.strip():
            return tier.strip()
        facts = sources.get("facts_v2_quality")
        if isinstance(facts, dict):
            tier2 = facts.get("tier")
            if isinstance(tier2, str) and tier2.strip():
                return tier2.strip()
    return ""


def run_scenario(base_url: str, token: str, scenario: Scenario) -> dict[str, Any]:
    print(f"\n=== Scenario: {scenario.name} ===", flush=True)
    payload: dict[str, Any] = {"product_description": scenario.product_description}
    if scenario.topic_profile_id:
        payload["topic_profile_id"] = scenario.topic_profile_id
    if scenario.mode:
        payload["mode"] = scenario.mode
    if scenario.audit_level:
        payload["audit_level"] = scenario.audit_level

    create_url = f"{base_url}/analyze"
    t0 = _now_ms()
    code, obj, raw = _http_json(method="POST", url=create_url, token=token, payload=payload)
    if code != 201 or obj is None:
        return {
            "name": scenario.name,
            "ok": False,
            "error": f"create analyze failed http={code} body={raw[:300]}",
        }

    task_id = str(obj.get("task_id") or "").strip()
    if not task_id:
        return {
            "name": scenario.name,
            "ok": False,
            "error": "create response missing task_id",
        }
    print(f"[create] task_id={task_id}", flush=True)

    try:
        final_status = _poll_status(
            base_url=base_url,
            token=token,
            task_id=task_id,
            max_wait_seconds=scenario.max_wait_seconds,
            stop_on_next_action_in=scenario.stop_on_next_action_in,
        )
    except Exception as exc:
        final_status = {"error": str(exc)}

    ledger = _fetch_admin_ledger(base_url=base_url, token=token, task_id=task_id)
    sources_ledger = None
    tier = _extract_tier_from_ledger(ledger)
    if not tier:
        sources_ledger = _fetch_task_sources_ledger(base_url=base_url, token=token, task_id=task_id)
        tier = _extract_tier_from_sources_ledger(sources_ledger)
    report_code, report_raw = _fetch_report(base_url=base_url, token=token, task_id=task_id)

    elapsed_ms = _now_ms() - t0
    print(f"[result] http_report={report_code} tier={tier or '-'} elapsed_ms={elapsed_ms}", flush=True)

    ok = True
    if isinstance(final_status, dict) and final_status.get("error"):
        ok = False
        print(f"[assert] FAIL: status poll error: {final_status.get('error')}", flush=True)
    if scenario.expect_tier_in is not None and tier:
        if tier not in set(scenario.expect_tier_in):
            ok = False
            print(
                f"[assert] FAIL: tier={tier} not in {scenario.expect_tier_in}",
                flush=True,
            )
    elif scenario.expect_tier_in is not None and not tier:
        ok = False
        print("[assert] FAIL: cannot determine tier (admin ledger missing?)", flush=True)

    facts_summary: dict[str, Any] = {}
    if ledger and isinstance(ledger.get("facts_snapshot"), dict):
        fs = ledger["facts_snapshot"]
        facts_summary = {
            "tier": fs.get("tier"),
            "passed": fs.get("passed"),
            "status": fs.get("status"),
            "blocked_reason": fs.get("blocked_reason"),
        }
        pkg = fs.get("v2_package") if isinstance(fs.get("v2_package"), dict) else {}
        if isinstance(pkg, dict):
            dl = pkg.get("data_lineage") if isinstance(pkg.get("data_lineage"), dict) else {}
            sr = dl.get("source_range") if isinstance(dl.get("source_range"), dict) else {}
            facts_summary["source_range"] = sr
            facts_summary["sample_posts"] = len(pkg.get("sample_posts_db") or [])
            facts_summary["sample_comments"] = len(pkg.get("sample_comments_db") or [])
            agg = pkg.get("aggregates") if isinstance(pkg.get("aggregates"), dict) else {}
            comms = agg.get("communities") if isinstance(agg.get("communities"), list) else []
            facts_summary["agg_comments"] = sum(
                int(c.get("comments") or 0) for c in comms if isinstance(c, dict)
            )
        quality = fs.get("quality") if isinstance(fs.get("quality"), dict) else {}
        if isinstance(quality, dict):
            facts_summary["quality_flags"] = quality.get("flags")

    if scenario.require_comments:
        sample_comments = int(facts_summary.get("sample_comments") or 0)
        if sample_comments <= 0:
            ok = False
            print("[assert] FAIL: require_comments=true but sample_comments=0", flush=True)

    return {
        "name": scenario.name,
        "ok": ok,
        "task_id": task_id,
        "elapsed_ms": elapsed_ms,
        "final_status": final_status,
        "tier": tier,
        "report_http": report_code,
        "report_preview": report_raw[:400],
        "facts_summary": facts_summary,
        "ledger": ledger,
        "sources_ledger": sources_ledger,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        required=True,
        help="JSON 配置文件（见 sample）",
    )
    parser.add_argument(
        "--token",
        default="",
        help="JWT token（不填则读 PHASE106_TOKEN）",
    )
    parser.add_argument(
        "--out",
        default="",
        help="把结果写入 JSON 文件（可选）",
    )
    args = parser.parse_args(argv)

    cfg = _load_config(args.config)
    base_url = _require_str(cfg, "base_url").rstrip("/")
    token = (args.token or os.getenv("PHASE106_TOKEN", "")).strip()
    if not token:
        print("Missing token: pass --token or set PHASE106_TOKEN", file=sys.stderr)
        return 2

    scenarios = _parse_scenarios(cfg)

    results: list[dict[str, Any]] = []
    all_ok = True
    for scenario in scenarios:
        try:
            res = run_scenario(base_url, token, scenario)
        except Exception as exc:  # pragma: no cover - best effort script
            res = {"name": scenario.name, "ok": False, "error": str(exc)}
        results.append(res)
        all_ok = all_ok and bool(res.get("ok"))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(
                {"base_url": base_url, "results": results},
                fh,
                ensure_ascii=False,
                indent=2,
            )
        print(f"\n[write] {args.out}", flush=True)

    if not all_ok:
        print("\nMatrix FAILED", flush=True)
        return 1
    print("\nMatrix OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
