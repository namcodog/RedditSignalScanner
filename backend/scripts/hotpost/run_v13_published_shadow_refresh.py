from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(dotenv_path=ROOT / ".env")

from app.services.hotpost.card_content_generator import build_backfill_draft
from app.services.hotpost.card_content_generator import _rewrite_validated_text
from app.services.hotpost.card_content_polish import polish_generated_text
from app.services.hotpost.card_payload_store import load_published_cards, merge_published_cards
from app.services.hotpost.published_card_semantic_refresh import merge_semantic_refresh, semantic_change_summary
from app.services.hotpost.card_content_llm_router import resolve_card_content_llm_profile
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v1 as v1
from backend.scripts.evals import run_hotpost_v13_shadow_new_samples as v13_shadow


PLAN_KIND = "hotpost_v13_published_shadow_refresh"
PLAN_VERSION = 1
V13_PROFILE_ID = "hotpost_v13_title_standalone"
CARD_TIMEOUT_SECONDS = 240.0
TRANSIENT_GENERATION_ATTEMPTS = 3
TRANSIENT_GENERATION_RETRY_DELAY_SECONDS = 1.0
TRANSIENT_ERROR_MARKERS = (
    "LLMClientError",
    "SSLEOFError",
    "UNEXPECTED_EOF",
    "IncompleteRead",
    "Connection refused",
    "Connection reset",
    "RemoteDisconnected",
    "temporarily unavailable",
    "timed out",
    "NoneType",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate or apply V13 shadow refresh plans for published Hotpost cards.")
    parser.add_argument("--card-id", action="append", default=[], help="Refresh one published card_id. Repeatable.")
    parser.add_argument("--lane", action="append", choices=["signal", "hot", "breakdown"], default=[])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--output-prefix", type=Path)
    parser.add_argument("--apply-plan", type=Path)
    parser.add_argument("--approved-by-human", action="store_true")
    parser.add_argument("--allow-error-free-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


async def run(args: argparse.Namespace) -> dict[str, Any]:
    _validate_args(args)
    if args.apply_plan is not None:
        return apply_plan(
            args.apply_plan,
            approved_by_human=args.approved_by_human,
            allow_error_free_only=args.allow_error_free_only,
        )

    published = load_published_cards()
    completed = load_completed_card_ids(args.resume_from) if args.resume_from else set()
    selected = select_published_cards(
        published,
        card_ids=set(args.card_id),
        lanes=set(args.lane),
        limit=args.limit,
        offset=args.offset,
        completed_card_ids=completed,
    )
    rows = await refresh_cards(selected, workers=args.workers)
    plan_path, report_path = write_outputs(rows, output_prefix=args.output_prefix)
    return {
        "mode": "shadow",
        "selected": len(selected),
        "generated": sum(1 for row in rows if not row.get("error")),
        "failed": sum(1 for row in rows if row.get("error")),
        "plan_path": str(plan_path),
        "report_path": str(report_path),
    }


def select_published_cards(
    cards: list[dict[str, Any]],
    *,
    card_ids: set[str],
    lanes: set[str],
    limit: int | None,
    offset: int,
    completed_card_ids: set[str],
) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    for card in cards:
        card_id = str(card.get("card_id") or "")
        lane = str(card.get("lane") or "")
        if completed_card_ids and card_id in completed_card_ids:
            continue
        if card_ids and card_id not in card_ids:
            continue
        if lanes and lane not in lanes:
            continue
        matched.append(card)
    if offset:
        matched = matched[offset:]
    if limit is not None:
        matched = matched[:limit]
    return matched


async def refresh_cards(cards: list[dict[str, Any]], *, workers: int) -> list[dict[str, Any]]:
    rules = v1.load_card_content_rules()
    models = v1.load_card_content_models()
    profile = resolve_card_content_llm_profile(models=models, profile_id=V13_PROFILE_ID)
    if profile is None:
        raise ValueError(f"Missing LLM profile: {V13_PROFILE_ID}")
    banned = v1._all_banned_patterns(rules)
    semaphore = asyncio.Semaphore(workers)

    async def _runner(card: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            return await refresh_one_card(
                card,
                rules=rules,
                models=models,
                banned=banned,
                semantic_model=profile["semantic_model"],
                writer_model=profile["writer_model"],
            )

    return list(await asyncio.gather(*(_runner(card) for card in cards)))


async def refresh_one_card(
    card: dict[str, Any],
    *,
    rules: dict[str, Any],
    models: dict[str, Any],
    banned: list[str],
    semantic_model: str,
    writer_model: str,
) -> dict[str, Any]:
    card_id = str(card.get("card_id") or "")
    row = {
        "card_id": card_id,
        "lane": str(card.get("lane") or ""),
        "card_type": str(card.get("card_type") or ""),
        "profile_id": V13_PROFILE_ID,
        "semantic_model": semantic_model,
        "writer_model": writer_model,
        "semantic_brief": {},
        "original_card": card,
        "v12_shadow": {},
        "refreshed_card": {},
        "changed": {},
        "fluency_repair_issue_count": 0,
        "remaining_density_issues": [],
        "v13_title_issues_before": [],
        "v13_title_issues_after": [],
        "error": "",
    }
    try:
        draft = build_backfill_draft(card)
        (
            _baseline,
            semantic_brief,
            v12_generated,
            v13_generated,
            fluency_issues,
            density_issues,
            title_before,
            title_after,
        ) = _unpack_shadow_generation_result(
            await _generate_shadow_with_retries(
                draft,
                rules=rules,
                models=models,
                banned=banned,
                semantic_model=semantic_model,
                writer_model=writer_model,
            )
        )
        row["semantic_brief"] = semantic_brief
        v13_generated = rewrite_generated_candidate(v13_generated, rules=rules)
        density_issues = v13_shadow.v12.find_v12_density_issues(v13_generated)
        title_after = v13_shadow.v13.find_v13_title_issues(v13_generated)
        refreshed = merge_semantic_refresh(card, v13_generated)
        row["v12_shadow"] = v12_generated
        row["refreshed_card"] = refreshed
        row["changed"] = semantic_change_summary(card, refreshed)
        row["fluency_repair_issue_count"] = len(fluency_issues)
        row["remaining_density_issues"] = density_issues
        row["v13_title_issues_before"] = title_before
        row["v13_title_issues_after"] = title_after
    except asyncio.TimeoutError:
        row["error"] = f"TimeoutError: card generation exceeded {CARD_TIMEOUT_SECONDS:.0f}s"
    except Exception as exc:  # noqa: BLE001 - shadow report should preserve per-card failures.
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


async def _generate_shadow_with_retries(
    draft: Any,
    *,
    rules: dict[str, Any],
    models: dict[str, Any],
    banned: list[str],
    semantic_model: str,
    writer_model: str,
) -> tuple[Any, ...]:
    last_error: Exception | None = None
    for attempt in range(TRANSIENT_GENERATION_ATTEMPTS):
        try:
            return await asyncio.wait_for(
                v13_shadow.generate_v13_shadow(
                    draft,
                    rules=rules,
                    models=models,
                    banned=banned,
                    semantic_model=semantic_model,
                    writer_model=writer_model,
                ),
                timeout=CARD_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            raise
        except Exception as exc:  # noqa: BLE001 - shadow retry should classify provider/network failures.
            last_error = exc
            if attempt >= TRANSIENT_GENERATION_ATTEMPTS - 1 or not _is_transient_generation_error(exc):
                raise
            await asyncio.sleep(TRANSIENT_GENERATION_RETRY_DELAY_SECONDS)
    raise last_error or RuntimeError("shadow generation failed")


def _unpack_shadow_generation_result(
    result: tuple[Any, ...],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[str], list[str], list[str], list[str]]:
    if len(result) == 8:
        baseline, semantic_brief, v12_generated, v13_generated, fluency_issues, density_issues, title_before, title_after = result
        return (
            dict(baseline or {}),
            dict(semantic_brief or {}),
            dict(v12_generated or {}),
            dict(v13_generated or {}),
            list(fluency_issues or []),
            list(density_issues or []),
            list(title_before or []),
            list(title_after or []),
        )
    if len(result) == 7:
        baseline, v12_generated, v13_generated, fluency_issues, density_issues, title_before, title_after = result
        return (
            dict(baseline or {}),
            {},
            dict(v12_generated or {}),
            dict(v13_generated or {}),
            list(fluency_issues or []),
            list(density_issues or []),
            list(title_before or []),
            list(title_after or []),
        )
    raise ValueError(f"unexpected V13 shadow generation result length: {len(result)}")


def _is_transient_generation_error(exc: Exception) -> bool:
    text = f"{type(exc).__name__}: {exc}"
    return any(marker in text for marker in TRANSIENT_ERROR_MARKERS)


def rewrite_generated_candidate(candidate: dict[str, Any], *, rules: dict[str, Any]) -> dict[str, Any]:
    rewritten: dict[str, Any] = {}
    for key, value in candidate.items():
        if isinstance(value, str):
            rewritten[key] = polish_generated_text(
                _rewrite_validated_text(value, rules),
                field_name=_field_name_for_polish(key),
            )
        elif isinstance(value, dict):
            rewritten[key] = rewrite_generated_candidate(value, rules=rules)
        else:
            rewritten[key] = value
    return rewritten


def _field_name_for_polish(key: str) -> str:
    if key in {"title", "summary_line", "audience", "why_now", "why_test_now", "continue_signal", "stop_signal"}:
        return key
    return "detail"


def write_outputs(rows: list[dict[str, Any]], *, output_prefix: Path | None) -> tuple[Path, Path]:
    if output_prefix is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_prefix = v1.REPORTS_EVALS_DIR / f"hotpost_v13_published_shadow_{stamp}"
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    plan_path = output_prefix.with_suffix(".json")
    report_path = output_prefix.with_suffix(".md")
    plan = build_plan(rows)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(render_report(plan), encoding="utf-8")
    return plan_path, report_path


def build_plan(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "kind": PLAN_KIND,
        "plan_version": PLAN_VERSION,
        "profile_id": V13_PROFILE_ID,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "selected": len(rows),
        "generated": sum(1 for row in rows if not row.get("error")),
        "failed": sum(1 for row in rows if row.get("error")),
        "cards": rows,
    }


def render_report(plan: dict[str, Any]) -> str:
    rows = plan.get("cards") if isinstance(plan.get("cards"), list) else []
    lines = [
        "# Hotpost V13 Published Shadow Refresh 审核包",
        "",
        "这份报告只读生成，不改 drafts / published / release，也不切默认生产流量。",
        "",
        f"- selected: `{plan.get('selected', 0)}`",
        f"- generated: `{plan.get('generated', 0)}`",
        f"- failed: `{plan.get('failed', 0)}`",
        f"- profile: `{plan.get('profile_id', V13_PROFILE_ID)}`",
        "",
        "## 总览",
        "",
    ]
    for row in rows:
        status = "失败" if row.get("error") else "成功"
        title_issues = len(row.get("v13_title_issues_after") or [])
        lines.append(f"- `{row.get('lane')}` `{row.get('card_id')}`: {status}，title 残留 `{title_issues}`")
    lines.append("")
    for row in rows:
        lines.extend(_render_row(row))
    return "\n".join(lines).rstrip() + "\n"


def _render_row(row: dict[str, Any]) -> list[str]:
    original = row.get("original_card") if isinstance(row.get("original_card"), dict) else {}
    refreshed = row.get("refreshed_card") if isinstance(row.get("refreshed_card"), dict) else {}
    lines = [
        f"## {row.get('lane')} · {row.get('card_id')}",
        "",
        f"- card_type: `{row.get('card_type')}`",
        f"- model route: `{row.get('semantic_model')} -> {row.get('writer_model')}`",
        f"- source: {original.get('source_link', '')}",
        "",
    ]
    if row.get("error"):
        lines.extend(["**生成失败**", "", f"- {row['error']}", ""])
        return lines
    lines.extend(_render_fields("原卡", original))
    lines.extend(_render_semantic_brief("语义理解 brief", row.get("semantic_brief") or {}))
    lines.extend(_render_fields("V13 候选新版", refreshed))
    lines.extend(
        [
            "**自动检查**",
            "",
            f"- changed fields: `{len(row.get('changed') or {})}`",
            f"- V11 中文顺读 repair 触发问题数：`{row.get('fluency_repair_issue_count', 0)}`",
            f"- V12 高密度残留问题：`{len(row.get('remaining_density_issues') or [])}`",
            f"- V13 title 修前问题：`{len(row.get('v13_title_issues_before') or [])}`",
            f"- V13 title 修后问题：`{len(row.get('v13_title_issues_after') or [])}`",
            "",
        ]
    )
    for issue in (row.get("v13_title_issues_after") or [])[:5]:
        lines.append(f"  - {issue}")
    if row.get("v13_title_issues_after"):
        lines.append("")
    return lines


def _render_fields(label: str, card: dict[str, Any]) -> list[str]:
    detail = card.get("detail") if isinstance(card.get("detail"), dict) else {}
    fields = {
        "title": card.get("title"),
        "summary_line": card.get("summary_line"),
        "audience": card.get("audience"),
        "why_now": card.get("why_now"),
    }
    lines = [f"**{label}**", ""]
    for key, value in fields.items():
        if value:
            lines.append(f"- `{key}`: {value}")
    for key, value in detail.items():
        if key == "min_test_action":
            continue
        lines.append(f"- `detail.{key}`: {value}")
    lines.append("")
    return lines


def _render_semantic_brief(label: str, brief: dict[str, Any]) -> list[str]:
    lines = [f"**{label}**", ""]
    for key in (
        "core_scene",
        "actor_and_scene",
        "supported_claim",
        "evidence_basis",
        "lane_specific",
        "tension_or_decision",
        "why_now_readout",
        "risk_bounds",
        "writing_focus",
        "avoid_claims",
        "uncertainty",
    ):
        value = brief.get(key)
        if value:
            rendered = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
            lines.append(f"- `{key}`: {rendered}")
    lines.append("")
    return lines


def load_completed_card_ids(path: Path) -> set[str]:
    raw = _load_plan(path)
    rows = raw.get("cards") if isinstance(raw.get("cards"), list) else []
    return {str(row.get("card_id")) for row in rows if isinstance(row, dict) and row.get("card_id") and not row.get("error")}


def apply_plan(path: Path, *, approved_by_human: bool, allow_error_free_only: bool) -> dict[str, Any]:
    if not approved_by_human:
        raise ValueError("--approved-by-human is required before applying refreshed published cards")
    plan = _load_plan(path)
    rows = plan["cards"]
    failed = [row for row in rows if row.get("error") or not row.get("refreshed_card")]
    if failed:
        raise ValueError(f"apply plan contains failed rows: {len(failed)}")
    if allow_error_free_only and plan.get("failed", 0):
        raise ValueError("apply plan is not error-free")
    refreshed = [row["refreshed_card"] for row in rows]
    merged = merge_published_cards(refreshed)
    return {
        "mode": "apply_plan",
        "selected": len(rows),
        "merged": merged,
        "skipped": len(rows) - merged,
        "apply_plan": str(path),
    }


def _load_plan(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"plan does not exist: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("plan must be a JSON object")
    if raw.get("kind") != PLAN_KIND:
        raise ValueError(f"plan kind must be {PLAN_KIND}")
    if raw.get("plan_version") != PLAN_VERSION:
        raise ValueError(f"plan version must be {PLAN_VERSION}")
    if raw.get("profile_id") != V13_PROFILE_ID:
        raise ValueError(f"plan profile_id must be {V13_PROFILE_ID}")
    if not isinstance(raw.get("cards"), list):
        raise ValueError("plan cards must be a list")
    return raw


def _validate_args(args: argparse.Namespace) -> None:
    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit must be greater than 0")
    if args.offset < 0:
        raise ValueError("--offset must be zero or greater")
    if args.workers <= 0:
        raise ValueError("--workers must be greater than 0")
    if args.apply_plan is not None:
        if args.card_id or args.lane or args.limit is not None or args.offset or args.resume_from or args.output_prefix:
            raise ValueError("--apply-plan cannot be combined with selectors, resume, or output options")


async def main() -> None:
    args = parse_args()
    result = await run(args)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
