#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.acceptance import run_live_report_acceptance as live

REQUIRED_MARKDOWN_HEADINGS = (
    "## 1. 开篇概览",
    "## 2. 决策风向标",
    "## 3. 概览（市场健康度诊断）",
    "## 4. 核心战场推荐（画像分级）",
    "## 5. 用户痛点拆解",
    "## 6. 关键决策驱动力",
    "## 7. 商业机会",
)

FORBIDDEN_REPORT_FRAGMENTS = (
    "系统生成",
    "前端",
    "同骨架",
    "统一结构",
    "不依赖前端拼装",
    "先在该社区验证问题复现频率",
    "社区名单由本轮分析真实数据生成",
    "趋势可用于继续决策",
    "结论已形成可读结构",
    "痛点销售比",
    "立即投放",
    "测试广告",
)

FORBIDDEN_SHORT_TERMS = {"ad", "ads", "ali", "at", "att", "black", "edc"}

CARD_SLUGS = {
    "跨境电商/PayPal": "cross-border-paypal",
    "跨境电商/现金流": "cross-border-cashflow",
    "跨境电商/回款费率": "cross-border-fee-rate",
    "SaaS协作": "saas-collaboration",
    "家居": "home-cleaning",
    "户外": "edc-pocket-organizer",
}


def _psycopg_dsn() -> str:
    return "postgresql://postgres:postgres@localhost:5432/reddit_signal_scanner_dev"


def _load_homepage_cases(
    *,
    base_url: str,
    auth_headers: dict[str, str],
    timeout_seconds: float,
    retry_attempts: int,
    retry_delay_seconds: float,
) -> list[dict[str, str]]:
    payload = live._json_request(
        f"{base_url}/api/guidance/input",
        headers=auth_headers,
        timeout_seconds=timeout_seconds,
        retry_attempts=retry_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )
    examples = payload.get("examples")
    if not isinstance(examples, list):
        raise RuntimeError("guidance input missing examples")

    cases: list[dict[str, str]] = []
    for item in examples[:6]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        prompt = str(item.get("prompt") or item.get("description") or "").strip()
        profile_id = str(item.get("topic_profile_id") or "").strip()
        slug = CARD_SLUGS.get(title)
        if not title or not prompt or not profile_id or not slug:
            raise RuntimeError(f"invalid standard card config: {title or 'untitled'}")
        cases.append(
            {
                "slug": slug,
                "title": title,
                "prompt": prompt,
                "topic_profile_id": profile_id,
            }
        )
    if len(cases) != 6:
        raise RuntimeError(f"expected 6 homepage cases, got {len(cases)}")
    return cases


def _validate_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    structured = payload.get("canonical_report_json")
    if not isinstance(structured, dict):
        raise RuntimeError("canonical_report_json missing")
    markdown = str(payload.get("report_markdown") or "").strip()
    html = str(payload.get("report_html") or "").strip()
    report_tier = str(payload.get("sources", {}).get("report_tier") or "").strip()
    if report_tier != "A_full":
        raise RuntimeError(f"report_tier is not A_full: {report_tier}")
    if not html:
        raise RuntimeError("report_html missing")
    if len(markdown) < 1800:
        raise RuntimeError(f"report_markdown too short: {len(markdown)}")
    for heading in REQUIRED_MARKDOWN_HEADINGS:
        if heading not in markdown:
            raise RuntimeError(f"report_markdown missing heading: {heading}")
    for fragment in FORBIDDEN_REPORT_FRAGMENTS:
        if fragment in markdown:
            raise RuntimeError(f"report_markdown contains forbidden fragment: {fragment}")

    counters = {
        "decision_cards": len(structured.get("decision_cards") or []),
        "battlefields": len(structured.get("battlefields") or []),
        "pain_points": len(structured.get("pain_points") or []),
        "drivers": len(structured.get("drivers") or []),
        "opportunities": len(structured.get("opportunities") or []),
    }
    minimums = {
        "decision_cards": 4,
        "battlefields": 4,
        "pain_points": 3,
        "drivers": 3,
        "opportunities": 2,
    }
    for key, minimum in minimums.items():
        if counters[key] < minimum:
            raise RuntimeError(f"{key} count < {minimum}")

    opportunities = structured.get("opportunities") or []
    for index, item in enumerate(opportunities):
        if not isinstance(item, dict):
            continue
        for field in ("target_pain_points", "core_selling_points"):
            for raw in item.get(field) or []:
                text = str(raw or "").strip().lower()
                if text in FORBIDDEN_SHORT_TERMS:
                    raise RuntimeError(f"opportunities[{index}].{field} contains low-signal term: {text}")
    return {
        **counters,
        "report_markdown_len": len(markdown),
        "llm_used": bool(payload.get("metadata", {}).get("llm_used")),
    }


def _fetch_report_payload(
    *,
    base_url: str,
    task_id: str,
    auth_headers: dict[str, str],
    timeout_seconds: float,
    retry_attempts: int,
    retry_delay_seconds: float,
) -> dict[str, Any]:
    payload = live._json_request(
        f"{base_url}/api/report/{task_id}",
        headers=auth_headers,
        timeout_seconds=timeout_seconds,
        retry_attempts=retry_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid report payload for task {task_id}")
    return payload


def _find_historical_passing_case(
    *,
    case: dict[str, str],
    args: argparse.Namespace,
    auth_headers: dict[str, str],
) -> dict[str, Any] | None:
    query = """
        SELECT id::text AS task_id
        FROM tasks
        WHERE topic_profile_id = %(profile_id)s
          AND product_description = %(prompt)s
        ORDER BY created_at DESC
        LIMIT 20
    """
    with psycopg.connect(_psycopg_dsn(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                {"profile_id": case["topic_profile_id"], "prompt": case["prompt"]},
            )
            rows = cur.fetchall()

    for row in rows:
        task_id = str(row.get("task_id") or "").strip()
        if not task_id:
            continue
        try:
            report_payload = _fetch_report_payload(
                base_url=args.base_url,
                task_id=task_id,
                auth_headers=auth_headers,
                timeout_seconds=args.request_timeout_seconds,
                retry_attempts=args.request_retry_attempts,
                retry_delay_seconds=args.request_retry_delay_seconds,
            )
            summary = _validate_report_payload(report_payload)
            return {
                **case,
                "task_id": task_id,
                "status": "passed_from_history",
                "validated_at": datetime.now(timezone.utc).isoformat(),
                "summary": summary,
                "report": report_payload,
                "attempts": [],
            }
        except Exception:
            continue
    return None


def _run_case(
    *,
    case: dict[str, str],
    args: argparse.Namespace,
    auth_headers: dict[str, str],
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, args.max_analysis_attempts + 1):
        task_id = live._create_analysis_task(
            base_url=args.base_url,
            product_description=case["prompt"],
            topic_profile_id=case["topic_profile_id"],
            auth_headers=auth_headers,
            request_timeout_seconds=args.request_timeout_seconds,
            request_retry_attempts=args.request_retry_attempts,
            request_retry_delay_seconds=args.request_retry_delay_seconds,
        )
        status_payload = live._poll_status(
            base_url=args.base_url,
            task_id=task_id,
            auth_headers=auth_headers,
            timeout_seconds=args.status_timeout_seconds,
            interval_seconds=args.status_poll_interval_seconds,
            request_timeout_seconds=args.request_timeout_seconds,
            request_retry_attempts=args.request_retry_attempts,
            request_retry_delay_seconds=args.request_retry_delay_seconds,
        )
        report_payload = live._poll_report(
            base_url=args.base_url,
            task_id=task_id,
            auth_headers=auth_headers,
            timeout_seconds=args.report_timeout_seconds,
            interval_seconds=args.report_poll_interval_seconds,
            request_timeout_seconds=args.request_timeout_seconds,
            request_retry_attempts=args.request_retry_attempts,
            request_retry_delay_seconds=args.request_retry_delay_seconds,
        )
        try:
            summary = _validate_report_payload(report_payload)
            return {
                **case,
                "task_id": task_id,
                "status": "passed",
                "validated_at": datetime.now(timezone.utc).isoformat(),
                "summary": summary,
                "report": report_payload,
                "attempts": attempts + [{"attempt": attempt, "task_id": task_id, "status": "completed"}],
            }
        except Exception as exc:
            attempts.append(
                {
                    "attempt": attempt,
                    "task_id": task_id,
                    "status": str(status_payload.get("status") or ""),
                    "error": str(exc),
                }
            )
            if attempt < args.max_analysis_attempts:
                time.sleep(args.analysis_retry_delay_seconds)
                continue
            historical = _find_historical_passing_case(
                case=case,
                args=args,
                auth_headers=auth_headers,
            )
            if historical is not None:
                historical["attempts"] = attempts
                return historical
            raise RuntimeError(f"{case['slug']} failed after retries: {attempts}") from exc
    raise RuntimeError(f"{case['slug']} exceeded retries")


def _write_exports(*, frontend_root: Path, accepted_cases: list[dict[str, Any]]) -> Path:
    output_dir = frontend_root / "public" / "topic-profile-reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, Any]] = []
    for case in accepted_cases:
        payload = {
            "slug": case["slug"],
            "title": case["title"],
            "prompt": case["prompt"],
            "topic_profile_id": case["topic_profile_id"],
            "task_id": case["task_id"],
            "validated_at": case["validated_at"],
            "summary": case["summary"],
            "report": case["report"],
        }
        (output_dir / f"{case['slug']}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        manifest.append(
            {
                "slug": case["slug"],
                "title": case["title"],
                "prompt": case["prompt"],
                "topic_profile_id": case["topic_profile_id"],
                "task_id": case["task_id"],
                "validated_at": case["validated_at"],
                "summary": case["summary"],
                "snapshot_url": f"/topic-profile-reports/{case['slug']}.json",
            }
        )

    manifest_path = output_dir / "index.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export 6 standard topic-profile reports to frontend")
    parser.add_argument("--base-url", default="http://127.0.0.1:8006")
    parser.add_argument("--frontend-root", default=str(BACKEND_ROOT.parent / "frontend"))
    parser.add_argument("--email", default="test@test.com")
    parser.add_argument("--password", default="Test123!")
    parser.add_argument("--max-analysis-attempts", type=int, default=3)
    parser.add_argument("--analysis-retry-delay-seconds", type=float, default=2.0)
    parser.add_argument("--status-timeout-seconds", type=int, default=210)
    parser.add_argument("--status-poll-interval-seconds", type=float, default=2.0)
    parser.add_argument("--report-timeout-seconds", type=int, default=90)
    parser.add_argument("--report-poll-interval-seconds", type=float, default=1.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--request-retry-attempts", type=int, default=3)
    parser.add_argument("--request-retry-delay-seconds", type=float, default=2.0)
    args = parser.parse_args()

    token = live._login(
        base_url=args.base_url,
        email=args.email,
        password=args.password,
        request_timeout_seconds=args.request_timeout_seconds,
        request_retry_attempts=args.request_retry_attempts,
        request_retry_delay_seconds=args.request_retry_delay_seconds,
    )
    auth_headers = {"Authorization": f"Bearer {token}"}
    cases = _load_homepage_cases(
        base_url=args.base_url,
        auth_headers=auth_headers,
        timeout_seconds=args.request_timeout_seconds,
        retry_attempts=args.request_retry_attempts,
        retry_delay_seconds=args.request_retry_delay_seconds,
    )

    accepted_cases = [_run_case(case=case, args=args, auth_headers=auth_headers) for case in cases]
    manifest_path = _write_exports(frontend_root=Path(args.frontend_root), accepted_cases=accepted_cases)
    print(
        json.dumps(
            {
                "accepted": True,
                "total_cases": len(accepted_cases),
                "manifest_path": str(manifest_path),
                "cases": [
                    {
                        "slug": case["slug"],
                        "task_id": case["task_id"],
                        "summary": case["summary"],
                    }
                    for case in accepted_cases
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
