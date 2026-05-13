#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

# Ensure script can import backend modules regardless of launch directory.
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.report.content_guardrails import (  # noqa: E402
    is_low_signal_opportunity_title,
    is_placeholder_pain_title,
)
from app.services.discovery.warzone_classifier import WarzoneClassifier  # noqa: E402
from scripts.acceptance import run_live_report_acceptance as live  # noqa: E402

_GENERIC_SCAFFOLD_PAIN_RE = re.compile(
    r"^围绕「.+」反复出现的关键麻烦(?:（场景\d+(?:-\d+)?）)?$"
)
_GENERIC_SCAFFOLD_OPPORTUNITY_RE = re.compile(
    r"^围绕「.+」的产品机会(?:（场景\d+(?:-\d+)?）)?$"
)

DEFAULT_SMOKE_CASES: tuple[dict[str, Any], ...] = (
    {
        "label": "PayPal_Ecommerce",
        "expected_warzone": "Ecommerce_Business",
        "community_hints": ("stripe", "paypal", "shopify", "ecommerce", "payment"),
        "product_description": "我做跨境电商卖家，最近 PayPal 和 Stripe 回款慢、退款手续费高，现金流很紧，想找到可落地的资金管理切口。",
    },
    {
        "label": "Tools_EDC",
        "expected_warzone": "Tools_EDC",
        "community_hints": ("edc", "flashlight", "knife", "multitool", "tools"),
        "product_description": (
            "我想研究 EDC（everyday carry）里钥匙、门禁卡、小刀、手电在口袋里打架的真实痛点，"
            "重点关注 pocket organizer、quick access、bulk、carry comfort、重复携带，"
            "判断有没有能直接落地的小配件产品机会。"
        ),
    },
    {
        "label": "Family_Parenting",
        "expected_warzone": "Family_Parenting",
        "community_hints": ("parent", "newparent", "baby", "breastfeeding", "daddit", "beyondthebump"),
        "product_description": "我们是新手父母，夜奶和睡眠记录总断档，家人换手照护时经常漏项，想知道有没有真实可行的产品切口。",
    },
)

DEFAULT_FINAL_DESCRIPTION = (
    "我做跨境电商独立站，最近订单上涨但回款和退款争议让现金流持续紧张，"
    "希望基于 Reddit 真实讨论找到一个能直接执行的产品机会。"
)


def _txt(value: Any) -> str:
    return str(value or "").strip()


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _pick_titles(value: Any) -> list[str]:
    output: list[str] = []
    for item in _list(value):
        if isinstance(item, Mapping):
            title = _txt(item.get("title") or item.get("description"))
        else:
            title = _txt(item)
        if title:
            output.append(title)
    return output


def _collect_evidence_urls(value: Any) -> list[str]:
    urls: list[str] = []
    for item in _list(value):
        if not isinstance(item, Mapping):
            continue
        for evidence in _list(item.get("evidence_chain")):
            if not isinstance(evidence, Mapping):
                continue
            url = _txt(evidence.get("url"))
            if url:
                urls.append(url)
    return urls


def _is_clickable_reddit_url(url: str) -> bool:
    lowered = _txt(url).lower()
    if not lowered.startswith(("http://", "https://")):
        return False
    return "reddit.com/" in lowered


def _extract_remediation_blockers(report_payload: Mapping[str, Any]) -> list[str]:
    sources = report_payload.get("sources") if isinstance(report_payload.get("sources"), Mapping) else {}
    blockers: list[str] = []
    for action in _list((sources or {}).get("remediation_actions")):
        if not isinstance(action, Mapping):
            continue
        action_type = _txt(action.get("type"))
        action_blocked = _txt(action.get("blocked_reason"))
        try:
            targets = int(action.get("targets") or 0)
        except (TypeError, ValueError):
            targets = 0
        if action_type == "backfill_posts" and targets <= 0 and action_blocked:
            blockers.append(action_blocked)
    return list(dict.fromkeys(blockers))


def _should_stop_retrying(
    *,
    blocked_reason: str,
    next_action: str,
    remediation_blockers: Sequence[str],
) -> bool:
    if next_action == "manual_intervention":
        return True
    if blocked_reason != "insufficient_samples":
        return False
    return any(
        blocker in {"budget_or_fuse_blocked", "budget_blocked", "fuse_blocked"}
        for blocker in remediation_blockers
    )


def _load_warzone_classifier() -> WarzoneClassifier | None:
    config_path = BACKEND_ROOT / "config" / "warzones.yaml"
    if not config_path.exists():
        return None
    try:
        return WarzoneClassifier(config_path)
    except Exception:
        return None


def _semantic_warzone_mismatch(
    *,
    expected_warzone: str,
    text: str,
    classifier: WarzoneClassifier | None,
) -> bool:
    if not classifier:
        return False
    cleaned = _txt(text)
    if not cleaned:
        return False
    guess = classifier.classify_texts([cleaned])
    guessed = _txt(guess.warzone)
    confidence = float(guess.confidence or 0.0)
    if not guessed or guessed == "unknown" or confidence < 0.55:
        return False
    return guessed != expected_warzone


def _validate_report_contract(
    *,
    report_payload: Mapping[str, Any],
    required_tier: str,
    min_reddit_links: int,
    expected_warzone: str = "",
    community_hints: Sequence[str] = (),
    classifier: WarzoneClassifier | None = None,
) -> tuple[list[str], dict[str, Any]]:
    issues: list[str] = []
    sources = report_payload.get("sources") if isinstance(report_payload.get("sources"), Mapping) else {}
    report_tier = _txt((sources or {}).get("report_tier"))
    blocked_reason = _txt((sources or {}).get("analysis_blocked"))

    if required_tier and report_tier != required_tier:
        issues.append(f"tier mismatch: expected={required_tier}, actual={report_tier or 'unknown'}")
    if blocked_reason:
        issues.append(f"analysis blocked: {blocked_reason}")

    structured = report_payload.get("canonical_report_json")
    if not isinstance(structured, Mapping):
        issues.append("canonical_report_json missing")
        return issues, {
            "report_tier": report_tier,
            "analysis_blocked": blocked_reason,
            "pain_titles": [],
            "opportunity_titles": [],
            "target_communities": [],
            "reddit_links": [],
        }

    pain_titles = _pick_titles(structured.get("pain_points"))
    opportunity_titles = _pick_titles(structured.get("opportunities"))
    target_communities = _pick_titles(structured.get("target_communities"))

    if len(pain_titles) < 3:
        issues.append(f"pain_points insufficient: {len(pain_titles)}")
    for title in pain_titles:
        if is_placeholder_pain_title(title):
            issues.append(f"placeholder pain title: {title}")
        if _GENERIC_SCAFFOLD_PAIN_RE.match(title):
            issues.append(f"generic scaffold pain title: {title}")
        if expected_warzone and _semantic_warzone_mismatch(
            expected_warzone=expected_warzone,
            text=title,
            classifier=classifier,
        ):
            issues.append(f"cross-warzone pain title: {title}")

    if len(opportunity_titles) < 2:
        issues.append(f"opportunities insufficient: {len(opportunity_titles)}")
    for title in opportunity_titles:
        if is_low_signal_opportunity_title(title):
            issues.append(f"low-signal opportunity title: {title}")
        if _GENERIC_SCAFFOLD_OPPORTUNITY_RE.match(title):
            issues.append(f"generic scaffold opportunity title: {title}")
        if expected_warzone and _semantic_warzone_mismatch(
            expected_warzone=expected_warzone,
            text=title,
            classifier=classifier,
        ):
            issues.append(f"cross-warzone opportunity title: {title}")

    if not target_communities:
        issues.append("target_communities missing")
    elif community_hints:
        lowered = [community.lower() for community in target_communities]
        hit_count = sum(
            1
            for community in lowered
            if any(hint in community for hint in community_hints)
        )
        if hit_count < 2:
            issues.append(
                f"target_communities domain hit too low: {hit_count} < 2 (hints={','.join(community_hints)})"
            )

    pain_reddit_links = [
        url for url in _collect_evidence_urls(structured.get("pain_points")) if _is_clickable_reddit_url(url)
    ]
    opportunity_reddit_links = [
        url
        for url in _collect_evidence_urls(structured.get("opportunities"))
        if _is_clickable_reddit_url(url)
    ]
    reddit_links = list(dict.fromkeys([*pain_reddit_links, *opportunity_reddit_links]))

    if not pain_reddit_links:
        issues.append("pain evidence has no clickable reddit link")
    if not opportunity_reddit_links:
        issues.append("opportunity evidence has no clickable reddit link")
    if len(reddit_links) < min_reddit_links:
        issues.append(f"reddit evidence links insufficient: {len(reddit_links)} < {min_reddit_links}")

    markdown = _txt(report_payload.get("report_markdown"))
    html = _txt(report_payload.get("report_html"))
    if not markdown and not html:
        issues.append("narrative report missing (report_markdown/report_html both empty)")
    if markdown and pain_titles and pain_titles[0] not in markdown:
        issues.append("markdown not aligned with canonical pain title")
    if markdown and opportunity_titles and opportunity_titles[0] not in markdown:
        issues.append("markdown not aligned with canonical opportunity title")

    return issues, {
        "report_tier": report_tier,
        "analysis_blocked": blocked_reason,
        "pain_titles": pain_titles,
        "opportunity_titles": opportunity_titles,
        "target_communities": target_communities,
        "reddit_links": reddit_links,
    }


def _run_single_case(
    *,
    label: str,
    product_description: str,
    expected_warzone: str,
    community_hints: Sequence[str],
    base_url: str,
    frontend_base_url: str,
    auth_headers: dict[str, str],
    required_tier: str,
    min_reddit_links: int,
    classifier: WarzoneClassifier | None,
    max_analysis_attempts: int,
    analysis_retry_delay_seconds: float,
    warmup_wait_timeout_seconds: int,
    warmup_poll_interval_seconds: float,
    status_timeout_seconds: int,
    status_poll_interval_seconds: float,
    report_timeout_seconds: int,
    report_poll_interval_seconds: float,
    request_timeout_seconds: float,
    request_retry_attempts: int,
    request_retry_delay_seconds: float,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []

    for attempt in range(1, max(1, max_analysis_attempts) + 1):
        started = time.time()
        task_id = live._create_analysis_task(
            base_url=base_url,
            product_description=product_description,
            topic_profile_id=None,
            auth_headers=auth_headers,
            request_timeout_seconds=request_timeout_seconds,
            request_retry_attempts=request_retry_attempts,
            request_retry_delay_seconds=request_retry_delay_seconds,
        )
        print(
            f"[open-question-live] label={label} attempt={attempt} task_id={task_id} created",
            flush=True,
        )

        status_payload = live._poll_status(
            base_url=base_url,
            task_id=task_id,
            auth_headers=auth_headers,
            timeout_seconds=status_timeout_seconds,
            interval_seconds=status_poll_interval_seconds,
            request_timeout_seconds=request_timeout_seconds,
            request_retry_attempts=request_retry_attempts,
            request_retry_delay_seconds=request_retry_delay_seconds,
        )
        status = _txt(status_payload.get("status")).lower()
        print(
            f"[open-question-live] label={label} attempt={attempt} task_id={task_id} status={status or 'unknown'} elapsed={round(time.time() - started, 1)}s",
            flush=True,
        )

        if status == "failed":
            attempts.append(
                {
                    "attempt": attempt,
                    "task_id": task_id,
                    "status": status,
                    "error": _txt(status_payload.get("error")) or "analysis failed",
                    "elapsed_seconds": round(time.time() - started, 1),
                }
            )
            if attempt < max_analysis_attempts:
                time.sleep(analysis_retry_delay_seconds)
                continue
            return {
                "label": label,
                "product_description": product_description,
                "accepted": False,
                "attempts": attempts,
                "result_url": f"{frontend_base_url}/report/{task_id}",
            }

        report_payload = live._poll_report(
            base_url=base_url,
            task_id=task_id,
            auth_headers=auth_headers,
            timeout_seconds=report_timeout_seconds,
            interval_seconds=report_poll_interval_seconds,
            request_timeout_seconds=request_timeout_seconds,
            request_retry_attempts=request_retry_attempts,
            request_retry_delay_seconds=request_retry_delay_seconds,
        )

        issues, summary = _validate_report_contract(
            report_payload=report_payload,
            required_tier=required_tier,
            min_reddit_links=min_reddit_links,
            expected_warzone=expected_warzone,
            community_hints=community_hints,
            classifier=classifier,
        )
        blocked_reason = _txt(summary.get("analysis_blocked"))
        next_action = _txt(status_payload.get("next_action"))
        stage = _txt(status_payload.get("stage"))
        remediation_blockers = _extract_remediation_blockers(report_payload)
        accepted = not issues
        warmup_waited_seconds: float | None = None
        warmup_timeout = False

        if (
            not accepted
            and blocked_reason == "insufficient_samples"
            and next_action in {"wait_for_warmup", "auto_rerun_scheduled"}
            and warmup_wait_timeout_seconds > 0
        ):
            waited = live._wait_for_warmup_upgrade(
                base_url=base_url,
                task_id=task_id,
                auth_headers=auth_headers,
                required_tier=required_tier,
                allow_blocked=False,
                timeout_seconds=warmup_wait_timeout_seconds,
                interval_seconds=warmup_poll_interval_seconds,
                request_timeout_seconds=request_timeout_seconds,
                request_retry_attempts=request_retry_attempts,
                request_retry_delay_seconds=request_retry_delay_seconds,
            )
            warmup_waited_seconds = (
                float(waited["warmup_waited_seconds"])
                if waited.get("warmup_waited_seconds") is not None
                else None
            )
            warmup_timeout = bool(waited.get("warmup_timeout") or False)
            blocked_reason = _txt(waited.get("analysis_blocked")) or blocked_reason
            next_action = _txt(waited.get("next_action")) or next_action
            stage = _txt(waited.get("stage")) or stage
            if waited.get("accepted"):
                accepted = True
                issues = []
            elif warmup_timeout:
                issues = list(dict.fromkeys([*issues, "warmup upgrade timeout"]))

        attempt_payload = {
            "attempt": attempt,
            "task_id": task_id,
            "status": status,
            "issues": issues,
            "elapsed_seconds": round(time.time() - started, 1),
            "result_url": f"{frontend_base_url}/report/{task_id}",
            "stage": stage,
            "next_action": next_action,
            "warmup_waited_seconds": warmup_waited_seconds,
            "warmup_timeout": warmup_timeout,
            "remediation_blockers": remediation_blockers,
            **summary,
        }
        attempts.append(attempt_payload)
        print(
            f"[open-question-live] label={label} attempt={attempt} task_id={task_id} accepted={accepted} issues={len(issues)}",
            flush=True,
        )
        if accepted:
            return {
                "label": label,
                "product_description": product_description,
                "accepted": True,
                "attempts": attempts,
                **attempt_payload,
            }

        if _should_stop_retrying(
            blocked_reason=blocked_reason,
            next_action=next_action,
            remediation_blockers=remediation_blockers,
        ):
            return {
                "label": label,
                "product_description": product_description,
                "accepted": False,
                "attempts": attempts,
                **attempt_payload,
            }

        if attempt < max_analysis_attempts:
            time.sleep(analysis_retry_delay_seconds)

    last = attempts[-1] if attempts else {}
    return {
        "label": label,
        "product_description": product_description,
        "accepted": False,
        "attempts": attempts,
        **last,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run open-question live acceptance with evidence-link checks")
    parser.add_argument("--suite", choices=("smoke", "final"), default="smoke")
    parser.add_argument("--base-url", default="http://127.0.0.1:8016")
    parser.add_argument("--frontend-base-url", default="http://127.0.0.1:3006")
    parser.add_argument("--email", default="test@test.com")
    parser.add_argument("--password", default="Test123!")
    parser.add_argument("--product-description", default=DEFAULT_FINAL_DESCRIPTION)
    parser.add_argument("--required-tier", default="A_full")
    parser.add_argument("--min-reddit-links", type=int, default=2)
    parser.add_argument("--max-analysis-attempts", type=int, default=2)
    parser.add_argument("--analysis-retry-delay-seconds", type=float, default=3.0)
    parser.add_argument("--warmup-wait-timeout-seconds", type=int, default=420)
    parser.add_argument("--warmup-poll-interval-seconds", type=float, default=15.0)
    parser.add_argument("--status-timeout-seconds", type=int, default=240)
    parser.add_argument("--status-poll-interval-seconds", type=float, default=2.0)
    parser.add_argument("--report-timeout-seconds", type=int, default=120)
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

    if args.suite == "smoke":
        cases = DEFAULT_SMOKE_CASES
    else:
        cases = (
            {
                "label": "Final_Open_Question",
                "expected_warzone": "",
                "community_hints": (),
                "product_description": args.product_description,
            },
        )
    classifier = _load_warzone_classifier()

    started = time.time()
    rows: list[dict[str, Any]] = []
    for case in cases:
        label = str(case.get("label") or "open_question")
        product_description = str(case.get("product_description") or "").strip()
        expected_warzone = str(case.get("expected_warzone") or "").strip()
        community_hints = tuple(str(item).lower() for item in case.get("community_hints") or ())
        try:
            rows.append(
                _run_single_case(
                    label=label,
                    product_description=product_description,
                    expected_warzone=expected_warzone,
                    community_hints=community_hints,
                    base_url=args.base_url,
                    frontend_base_url=args.frontend_base_url,
                    auth_headers=auth_headers,
                    required_tier=args.required_tier,
                    min_reddit_links=args.min_reddit_links,
                    classifier=classifier,
                    max_analysis_attempts=args.max_analysis_attempts,
                    analysis_retry_delay_seconds=args.analysis_retry_delay_seconds,
                    warmup_wait_timeout_seconds=args.warmup_wait_timeout_seconds,
                    warmup_poll_interval_seconds=args.warmup_poll_interval_seconds,
                    status_timeout_seconds=args.status_timeout_seconds,
                    status_poll_interval_seconds=args.status_poll_interval_seconds,
                    report_timeout_seconds=args.report_timeout_seconds,
                    report_poll_interval_seconds=args.report_poll_interval_seconds,
                    request_timeout_seconds=args.request_timeout_seconds,
                    request_retry_attempts=args.request_retry_attempts,
                    request_retry_delay_seconds=args.request_retry_delay_seconds,
                )
            )
        except Exception as exc:  # pragma: no cover - acceptance utility
            rows.append(
                {
                    "label": label,
                    "product_description": product_description,
                    "accepted": False,
                    "error": str(exc),
                }
            )

    output_dir = Path("reports/local-acceptance")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"open_question_live_{args.suite}_{int(time.time())}.json"
    output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "suite": args.suite,
        "output": str(output_path),
        "total": len(rows),
        "accepted": sum(1 for row in rows if row.get("accepted")),
        "failed": sum(1 for row in rows if not row.get("accepted")),
        "elapsed_seconds": round(time.time() - started, 1),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["failed"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except PermissionError as exc:  # pragma: no cover - acceptance utility
        print(f"run_open_question_live_acceptance failed: {exc}", file=sys.stderr)
        raise
    except Exception as exc:  # pragma: no cover - acceptance utility
        print(f"run_open_question_live_acceptance failed: {exc}", file=sys.stderr)
        raise
