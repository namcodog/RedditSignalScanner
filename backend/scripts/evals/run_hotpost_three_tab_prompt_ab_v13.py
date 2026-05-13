"""Three-tab Hotpost prompt A/B v13 standalone title comparison.

V12 is the baseline. V13 keeps the approved model route and only repairs title
so a user can understand the card without reading summary_line first.
Production prompts are untouched.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Any

from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v1 as v1
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v12 as v12
from app.services.hotpost.card_content_title_v13 import (
    build_title_independence_repair_messages as _build_runtime_title_repair_messages,
    find_v13_title_issues as _find_runtime_v13_title_issues,
    merge_title_repair as _merge_runtime_title_repair,
)


REPORTS_EVALS_DIR = v12.REPORTS_EVALS_DIR
SEMANTIC_MODEL = "google/gemini-3-flash-preview"
WRITER_MODEL = "deepseek/deepseek-v4-pro"
V12_RESULTS_PATH = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v12_high_density_concise_results.json"
TITLE_ONLY_FIELDS = {"title"}

VAGUE_TITLE_PATTERNS = (
    "这到底是什么",
    "所以呢",
    "这是什么",
    "它到底",
    "这事",
)
CLICKBAIT_TITLE_WORDS = v12.CLICKBAIT_COMPRESSION_WORDS
COMPACT_ENGLISH_ABBR_RE = re.compile(
    r"[\u4e00-\u9fff](?:AI|API|SEO|GEO|ROI|LLM|Claude|OpenAI|ChatGPT|Gemini|DeepSeek|Token|Tokens)"
    r"|(?:AI|API|SEO|GEO|ROI|LLM|Claude|OpenAI|ChatGPT|Gemini|DeepSeek|Token|Tokens)[\u4e00-\u9fff]"
)
REPORT_TITLE_WORDS = (
    "实际效用",
    "定义与",
    "遭评论区",
    "评估AI",
)
BUSINESS_CONTEXT_HINTS = (
    "移动端",
    "转化率",
    "checkout",
    "会话回放",
    "广告",
    "投放",
    "API 账单",
    "API账单",
    "模型账单",
    "客服",
    "CRM",
)
CONCRETE_SUBJECT_MARKERS = (
    "Shopify",
    "Amazon",
    "亚马逊",
    "Meta",
    "Google",
    "Claude",
    "OpenAI",
    "ChatGPT",
    "卖家",
    "商家",
    "店主",
    "电商",
    "开发者",
    "投手",
    "产品经理",
    "客服团队",
    "服务商",
    "厂商",
    "程序员",
    "评论区",
)


def load_v12_baseline_rows(path: Path = V12_RESULTS_PATH) -> dict[str, dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("v12 results must be a list")
    by_card_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        card_id = str(row.get("card_id") or "")
        if card_id:
            by_card_id[card_id] = row
    return by_card_id


def find_v13_title_issues(generated: dict[str, Any]) -> list[str]:
    return _find_runtime_v13_title_issues(generated)


def build_title_independence_repair_messages(
    *,
    generated: dict[str, Any],
    semantic_brief: dict[str, Any],
    issues: list[str],
) -> list[dict[str, str]]:
    return _build_runtime_title_repair_messages(
        generated=generated,
        semantic_brief=semantic_brief,
        issues=issues,
        semantic_model=SEMANTIC_MODEL,
        writer_model=WRITER_MODEL,
    )


def merge_title_repair(original: dict[str, Any], repaired: dict[str, Any]) -> dict[str, Any]:
    return _merge_runtime_title_repair(original, repaired)


async def repair_title_independence(
    original: dict[str, Any],
    *,
    semantic_brief: dict[str, Any],
    issues: list[str],
    model: str,
) -> dict[str, Any]:
    repaired = await v1._generate_json(
        model=model,
        timeout=90.0,
        messages=build_title_independence_repair_messages(
            generated=original,
            semantic_brief=semantic_brief,
            issues=issues,
        ),
        client_factory=lambda selected_model, selected_timeout: v1.build_card_content_client(
            selected_model,
            timeout=selected_timeout,
        ),
        max_tokens=1024,
        response_schema=None,
    )
    return merge_title_repair(original, repaired)


def render_v13_markdown_report(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Hotpost 三 Tab Prompt A/B v13 title-standalone 小样本报告",
        "",
        "这份报告只比较 title 是否能脱离 summary_line 独立看懂，不代表候选质量、发布 gate 或小程序 UI 变更。",
        "",
        "## 总览",
        "",
    ]
    lanes = sorted({str(row.get("lane") or "unknown") for row in rows})
    for lane in lanes:
        lane_rows = [row for row in rows if str(row.get("lane") or "unknown") == lane]
        baseline_ok = sum(1 for row in lane_rows if not row.get("baseline_error"))
        variant_ok = sum(1 for row in lane_rows if not row.get("variant_error"))
        lines.append(f"- `{lane}`: baseline {baseline_ok}/{len(lane_rows)} 成功，variant {variant_ok}/{len(lane_rows)} 成功")
    for lane in lanes:
        lines.extend(["", f"## {lane}", ""])
        for row in [row for row in rows if str(row.get("lane") or "unknown") == lane]:
            baseline = row.get("baseline") or {}
            variant = row.get("variant") or {}
            lines.extend(
                [
                    f"### {row.get('card_id')}",
                    "",
                    f"- model: `{row.get('model')}`",
                    f"- summary_line: {variant.get('summary_line') or baseline.get('summary_line') or ''}",
                    f"- issues before: {len(row.get('v13_title_issues_before') or [])}",
                    f"- issues after: {len(row.get('v13_title_issues_after') or [])}",
                    "",
                    f"- A title: {baseline.get('title') or ''}",
                    f"- B title: {variant.get('title') or ''}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    REPORTS_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v13_title_standalone_results.json"
    md_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v13_title_standalone_report.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_v13_markdown_report(rows), encoding="utf-8")
    return json_path, md_path


async def run_experiment(*, writer_model: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    model_label = "v12 baseline vs v13 title-standalone"
    for source in load_v12_baseline_rows().values():
        baseline = source.get("variant") or {}
        semantic_brief = source.get("semantic_brief") or {}
        variant = dict(baseline)
        variant_error = ""
        issues_before = find_v13_title_issues(variant)
        issues_after: list[str] = []
        try:
            variant = await repair_title_independence(
                variant,
                semantic_brief=semantic_brief,
                issues=issues_before,
                model=writer_model,
            )
            issues_after = find_v13_title_issues(variant)
            if issues_after:
                variant = await repair_title_independence(
                    variant,
                    semantic_brief=semantic_brief,
                    issues=issues_after,
                    model=writer_model,
                )
                issues_after = find_v13_title_issues(variant)
            if issues_after:
                raise ValueError("v13 title issues remain: " + "; ".join(issues_after[:6]))
        except Exception as exc:  # noqa: BLE001 - experiment report must keep moving.
            variant_error = f"{type(exc).__name__}: {exc}"
        rows.append(
            {
                "lane": source.get("lane"),
                "card_id": source.get("card_id"),
                "model": model_label,
                "semantic_model": SEMANTIC_MODEL,
                "writer_model": writer_model,
                "published": source.get("published") or {},
                "semantic_brief": semantic_brief,
                "baseline": baseline,
                "variant": variant,
                "baseline_error": source.get("variant_error") or "",
                "variant_error": variant_error,
                "v13_title_issues_before": issues_before,
                "v13_title_issues_after": issues_after,
            }
        )
        print(
            json.dumps(
                {
                    "event": "generated",
                    "lane": source.get("lane"),
                    "card_id": source.get("card_id"),
                    "model": model_label,
                    "title_issue_count_before": len(issues_before),
                    "title_issue_count_after": len(issues_after),
                    "variant_error": variant_error,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    return rows


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run three-tab Hotpost prompt A/B v13 standalone title")
    parser.add_argument("--writer-model", default=WRITER_MODEL)
    args = parser.parse_args()

    rows = await run_experiment(writer_model=args.writer_model.strip() or WRITER_MODEL)
    json_path, md_path = write_outputs(rows)
    print(
        json.dumps(
            {"event": "done", "json_path": str(json_path), "report_path": str(md_path), "row_count": len(rows)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
