#!/usr/bin/env python3
from __future__ import annotations

"""
Run full-A acceptance for the 6 homepage topic-profile cards.

Validation scope:
1) Real chain: login -> analyze -> status -> report
2) Full-A structure contract on report payload
3) Persistence contract in DB (tasks + analyses + reports)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

# Ensure script can import backend modules regardless of launch directory.
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.acceptance import run_live_report_acceptance as live

REQUIRED_STRUCTURED_KEYS = (
    "decision_cards",
    "market_health",
    "battlefields",
    "pain_points",
    "drivers",
    "opportunities",
)


def _load_homepage_cases(
    *,
    base_url: str,
    auth_headers: dict[str, str],
    request_timeout_seconds: float,
    request_retry_attempts: int,
    request_retry_delay_seconds: float,
    limit: int,
) -> list[dict[str, str]]:
    payload = live._json_request(
        f"{base_url}/api/guidance/input",
        headers=auth_headers,
        timeout_seconds=request_timeout_seconds,
        retry_attempts=request_retry_attempts,
        retry_delay_seconds=request_retry_delay_seconds,
    )
    examples = payload.get("examples")
    if not isinstance(examples, list):
        raise RuntimeError("guidance input missing examples list")
    cases: list[dict[str, str]] = []
    for item in examples[:limit]:
        if not isinstance(item, dict):
            continue
        description = str(item.get("description") or item.get("prompt") or "").strip()
        profile = str(item.get("topic_profile_id") or "").strip()
        title = str(item.get("title") or "").strip() or "untitled"
        if not description or not profile:
            raise RuntimeError(f"invalid homepage case: title={title!r}")
        cases.append(
            {
                "title": title,
                "description": description,
                "topic_profile_id": profile,
            }
        )
    if len(cases) != limit:
        raise RuntimeError(f"expected {limit} homepage cases, got {len(cases)}")
    return cases


def _ensure_non_empty(value: Any, *, field: str) -> str:
    text_value = str(value or "").strip()
    if not text_value:
        raise RuntimeError(f"empty field: {field}")
    return text_value


def _validate_full_a_contract(report_payload: dict[str, Any]) -> dict[str, Any]:
    sources = report_payload.get("sources")
    if not isinstance(sources, dict):
        raise RuntimeError("report payload missing sources")
    tier = str(sources.get("report_tier") or "").strip()
    if tier != "A_full":
        raise RuntimeError(f"report_tier is not A_full: {tier}")

    structured = report_payload.get("report_structured")
    if not isinstance(structured, dict):
        raise RuntimeError("report_structured missing or invalid")

    for key in REQUIRED_STRUCTURED_KEYS:
        if key not in structured:
            raise RuntimeError(f"report_structured missing key: {key}")

    decision_cards = structured.get("decision_cards")
    battlefields = structured.get("battlefields")
    pain_points = structured.get("pain_points")
    drivers = structured.get("drivers")
    opportunities = structured.get("opportunities")
    market_health = structured.get("market_health")

    if not isinstance(decision_cards, list) or len(decision_cards) < 4:
        raise RuntimeError("decision_cards count < 4")
    if not isinstance(battlefields, list) or len(battlefields) < 4:
        raise RuntimeError("battlefields count < 4")
    if not isinstance(pain_points, list) or len(pain_points) < 3:
        raise RuntimeError("pain_points count < 3")
    if not isinstance(drivers, list) or len(drivers) < 3:
        raise RuntimeError("drivers count < 3")
    if not isinstance(opportunities, list) or len(opportunities) < 2:
        raise RuntimeError("opportunities count < 2")
    if not isinstance(market_health, dict):
        raise RuntimeError("market_health missing")

    first_card = decision_cards[0] if decision_cards else {}
    if not isinstance(first_card, dict):
        raise RuntimeError("decision_cards[0] invalid")
    _ensure_non_empty(first_card.get("title"), field="decision_cards[0].title")
    _ensure_non_empty(first_card.get("conclusion"), field="decision_cards[0].conclusion")

    competition = market_health.get("competition_saturation")
    ps_ratio = market_health.get("ps_ratio")
    if not isinstance(competition, dict):
        raise RuntimeError("market_health.competition_saturation missing")
    if not isinstance(ps_ratio, dict):
        raise RuntimeError("market_health.ps_ratio missing")
    _ensure_non_empty(competition.get("level"), field="market_health.competition_saturation.level")
    _ensure_non_empty(ps_ratio.get("ratio"), field="market_health.ps_ratio.ratio")

    report_html = str(report_payload.get("report_html") or "").strip()
    if not report_html:
        raise RuntimeError("report_html missing")
    modern_markers = ("## 已分析赛道", "## 决策卡片")
    legacy_markers = ("## 指标概览", "## 核心战场推荐（社区）")
    if not (
        all(marker in report_html for marker in modern_markers)
        or all(marker in report_html for marker in legacy_markers)
    ):
        raise RuntimeError("report_html missing required market report markers")

    return {
        "decision_cards": len(decision_cards),
        "battlefields": len(battlefields),
        "pain_points": len(pain_points),
        "drivers": len(drivers),
        "opportunities": len(opportunities),
    }


def _psycopg_dsn() -> str:
    raw = str(os.getenv("DATABASE_URL") or "").strip()
    if not raw:
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "reddit_signal_scanner_dev")
        raw = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    return raw.replace("+asyncpg", "").replace("+psycopg", "")


def _fetch_persistence_row(task_id: str) -> dict[str, Any] | None:
    query = """
        SELECT
          t.id::text AS task_id,
          t.topic_profile_id AS topic_profile_id,
          a.id::text AS analysis_id,
          a.sources->>'report_tier' AS report_tier,
          CASE
            WHEN a.sources ? 'report_structured'
            THEN jsonb_typeof(a.sources->'report_structured')
            ELSE NULL
          END AS report_structured_type,
          COALESCE(
            jsonb_array_length(
              COALESCE(a.sources->'report_structured'->'decision_cards', '[]'::jsonb)
            ),
            0
          ) AS decision_cards_count,
          r.id::text AS report_id
        FROM tasks t
        LEFT JOIN analyses a ON a.task_id = t.id
        LEFT JOIN reports r ON r.analysis_id = a.id
        WHERE t.id = %s
    """
    with psycopg.connect(_psycopg_dsn(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (task_id,))
            row = cur.fetchone()
    return dict(row) if row else None


def _validate_persistence(*, task_id: str, expected_profile_id: str) -> dict[str, Any]:
    row = _fetch_persistence_row(task_id)
    if row is None:
        raise RuntimeError(f"task not found in DB: {task_id}")

    topic_profile_id = str(row.get("topic_profile_id") or "").strip()
    if topic_profile_id != expected_profile_id:
        raise RuntimeError(
            f"topic_profile_id mismatch: expected={expected_profile_id}, got={topic_profile_id}"
        )
    if not str(row.get("analysis_id") or "").strip():
        raise RuntimeError("analysis row missing")
    if not str(row.get("report_id") or "").strip():
        raise RuntimeError("report row missing")
    if str(row.get("report_tier") or "").strip() != "A_full":
        raise RuntimeError(f"db report_tier is not A_full: {row.get('report_tier')}")
    if str(row.get("report_structured_type") or "").strip() != "object":
        raise RuntimeError("db report_structured is not JSON object")
    if int(row.get("decision_cards_count") or 0) < 4:
        raise RuntimeError("db report_structured.decision_cards count < 4")
    return row


def _run_single_case(
    *,
    case: dict[str, str],
    args: argparse.Namespace,
    auth_headers: dict[str, str],
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []

    for attempt in range(1, max(1, args.max_analysis_attempts) + 1):
        task_id = live._create_analysis_task(
            base_url=args.base_url,
            product_description=case["description"],
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
        status = str(status_payload.get("status") or "").lower()
        if status == "failed":
            attempts.append(
                {"attempt": attempt, "task_id": task_id, "status": "failed", "error": status_payload.get("error")}
            )
            if attempt < args.max_analysis_attempts:
                time.sleep(args.analysis_retry_delay_seconds)
                continue
            break

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
        report_tier, blocked_reason = live._extract_report_state(
            report_payload=report_payload,
            status_payload=status_payload,
        )
        accepted = live._is_report_accepted(
            report_tier=report_tier,
            blocked_reason=blocked_reason,
            required_tier="A_full",
            allow_blocked=False,
        )
        if accepted:
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
            structure_summary = _validate_full_a_contract(report_payload)
            persistence = _validate_persistence(
                task_id=task_id,
                expected_profile_id=case["topic_profile_id"],
            )
            return {
                "title": case["title"],
                "topic_profile_id": case["topic_profile_id"],
                "task_id": task_id,
                "status": "passed",
                "report_tier": report_tier,
                "analysis_blocked": blocked_reason,
                "structure_summary": structure_summary,
                "persistence": persistence,
                "attempts": attempts + [{"attempt": attempt, "task_id": task_id, "status": "completed"}],
            }

        attempts.append(
            {
                "attempt": attempt,
                "task_id": task_id,
                "status": status,
                "report_tier": report_tier,
                "analysis_blocked": blocked_reason,
            }
        )
        if attempt < args.max_analysis_attempts:
            time.sleep(args.analysis_retry_delay_seconds)

    raise RuntimeError(
        f"case failed after max attempts: title={case['title']} profile={case['topic_profile_id']} attempts={attempts}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run full-A matrix acceptance for 6 homepage topic-profile cards"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8006")
    parser.add_argument("--email", default="test@test.com")
    parser.add_argument("--password", default="Test123!")
    parser.add_argument("--case-limit", type=int, default=6)
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
        request_timeout_seconds=args.request_timeout_seconds,
        request_retry_attempts=args.request_retry_attempts,
        request_retry_delay_seconds=args.request_retry_delay_seconds,
        limit=args.case_limit,
    )

    started = datetime.now(timezone.utc)
    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        case_result = _run_single_case(case=case, args=args, auth_headers=auth_headers)
        case_result["order"] = index
        results.append(case_result)

    output_payload = {
        "accepted": True,
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(results),
        "results": results,
    }
    output_dir = Path("reports/local-acceptance")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"topic_profile_full_a_matrix_{int(time.time())}.json"
    output_path.write_text(json.dumps(output_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**output_payload, "output_path": str(output_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - acceptance utility
        print(f"run_topic_profile_full_a_matrix failed: {exc}", file=sys.stderr)
        raise
