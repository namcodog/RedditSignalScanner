#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# Ensure script can import backend modules regardless of launch directory.
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.acceptance import run_live_report_acceptance as live

DEFAULT_WARZONE_CASES: tuple[tuple[str, str], ...] = (
    (
        "Ecommerce_Business",
        "我想研究跨境电商卖家在 Shopify Amazon PayPal Stripe 回款 手续费 风控冻结 上的真实痛点，判断有没有收款和资金管理工具机会。",
    ),
    (
        "Home_Lifestyle",
        "我想研究 home cleaning、vacuum、organization、storage 这些家庭清洁和收纳场景里的真实麻烦，尤其是灰尘、pet hair、small space 和 cleaning routine，判断有没有工具机会。",
    ),
    (
        "Tools_EDC",
        "我想研究 EDC everyday carry 里钥匙 门禁卡 小刀 手电 和 pocket organizer 的真实需求，判断有没有小配件和收纳产品机会。",
    ),
    (
        "AI_Workflow",
        "我想研究团队在 ChatGPT Claude Notion AI agent 和自动化 workflow 里的真实卡点，判断有没有 AI workflow 工具机会。",
    ),
    (
        "Family_Parenting",
        "我想研究新生儿家庭在夜奶 喂养 睡眠 routine 和 parenting 协作上的真实痛点，判断有没有育儿记录工具机会。",
    ),
    (
        "Food_Coffee_Lifestyle",
        "我想研究咖啡用户在 espresso grinder brew beans 奶泡 和家用咖啡机选择上的真实痛点，判断有没有咖啡辅助工具机会。",
    ),
    (
        "Minimal_Outdoor",
        "我想研究 onebag ultralight 露营 hiking travel packing 和 outdoor gear 收纳上的真实麻烦，判断有没有轻量户外收纳产品机会。",
    ),
    (
        "Frugal_Living",
        "我想研究 frugal 人群在 budget bill subscription save money 和个人财务管理上的真实问题，判断有没有省钱和账单管理工具机会。",
    ),
)


def _pick_titles(value: Any) -> list[str]:
    output: list[str] = []
    if not isinstance(value, list):
        return output
    for item in value:
        if isinstance(item, dict):
            title = str(item.get("title") or item.get("description") or "").strip()
        else:
            title = str(item or "").strip()
        if title:
            output.append(title)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 8-warzone live matrix acceptance")
    parser.add_argument("--base-url", default="http://127.0.0.1:8016")
    parser.add_argument("--frontend-base-url", default="http://127.0.0.1:3006")
    parser.add_argument("--email", default="test@test.com")
    parser.add_argument("--password", default="Test123!")
    parser.add_argument("--status-timeout-seconds", type=int, default=240)
    parser.add_argument("--status-poll-interval-seconds", type=float, default=2.0)
    parser.add_argument("--report-timeout-seconds", type=int, default=120)
    parser.add_argument("--report-poll-interval-seconds", type=float, default=1.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--request-retry-attempts", type=int, default=3)
    parser.add_argument("--request-retry-delay-seconds", type=float, default=2.0)
    args = parser.parse_args()

    started = time.time()
    token = live._login(
        base_url=args.base_url,
        email=args.email,
        password=args.password,
        request_timeout_seconds=args.request_timeout_seconds,
        request_retry_attempts=args.request_retry_attempts,
        request_retry_delay_seconds=args.request_retry_delay_seconds,
    )
    auth_headers = {"Authorization": f"Bearer {token}"}

    results: list[dict[str, Any]] = []
    for warzone, product_description in DEFAULT_WARZONE_CASES:
        case_started = time.time()
        try:
            task_id = live._create_analysis_task(
                base_url=args.base_url,
                product_description=product_description,
                topic_profile_id=None,
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
            sources = report_payload.get("sources") if isinstance(report_payload, dict) else {}
            structured = report_payload.get("canonical_report_json") if isinstance(report_payload, dict) else {}
            structured = structured if isinstance(structured, dict) else {}
            results.append(
                {
                    "expected_warzone": warzone,
                    "product_description": product_description,
                    "task_id": task_id,
                    "status": str(status_payload.get("status") or ""),
                    "report_tier": str((sources or {}).get("report_tier") or ""),
                    "analysis_blocked": str(
                        (sources or {}).get("analysis_blocked")
                        or status_payload.get("blocked_reason")
                        or ""
                    ),
                    "next_action": str(status_payload.get("next_action") or ""),
                    "stage": str(status_payload.get("stage") or ""),
                    "pain_titles": _pick_titles(structured.get("pain_points")),
                    "opportunity_titles": _pick_titles(structured.get("opportunities")),
                    "community_titles": _pick_titles(structured.get("target_communities")),
                    "result_url": f"{args.frontend_base_url}/report/{task_id}",
                    "elapsed_seconds": round(time.time() - case_started, 1),
                }
            )
        except Exception as exc:  # pragma: no cover - acceptance utility
            results.append(
                {
                    "expected_warzone": warzone,
                    "product_description": product_description,
                    "error": str(exc),
                    "elapsed_seconds": round(time.time() - case_started, 1),
                }
            )

    output_dir = Path("reports/local-acceptance")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"warzone_live_matrix_final_{int(time.time())}.json"
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "output": str(output_path),
        "total": len(results),
        "a_full": sum(1 for row in results if row.get("report_tier") == "A_full"),
        "b_trimmed": sum(1 for row in results if row.get("report_tier") == "B_trimmed"),
        "c_scouting": sum(1 for row in results if row.get("report_tier") == "C_scouting"),
        "errors": sum(1 for row in results if "error" in row),
        "elapsed_seconds": round(time.time() - started, 1),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - CLI utility
        print(f"run_warzone_live_matrix failed: {exc}", file=sys.stderr)
        raise
