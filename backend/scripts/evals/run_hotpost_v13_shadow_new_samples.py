"""Run Hotpost V13 title-standalone shadow generation on fresh review samples.

This runner is read-only. It does not publish cards, update drafts, switch
default production traffic, or wire the V13 eval script into production.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v1 as v1
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v9 as v9
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v11 as v11
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v12 as v12
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v13 as v13
from backend.scripts.evals import run_hotpost_v12_shadow_new_samples as v12_shadow
from app.services.hotpost.card_content_llm_router import resolve_card_content_llm_profile


REPORT_JSON_PATH = v1.REPORTS_EVALS_DIR / "hotpost_v13_shadow_new_samples_results.json"
REPORT_MD_PATH = v1.REPORTS_EVALS_DIR / "hotpost_v13_shadow_new_samples_review_packet.md"
V13_PROFILE_ID = "hotpost_v13_title_standalone"
CARD_TIMEOUT_SECONDS = 240.0


async def generate_v13_shadow(
    draft: Any,
    *,
    rules: dict[str, Any],
    models: dict[str, Any],
    banned: list[str],
    semantic_model: str,
    writer_model: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[str], list[str], list[str], list[str]]:
    baseline = v1.extract_fields(draft)
    if not baseline.get("title"):
        baseline["title"] = draft.title
    print(json.dumps({"event": "phase", "card_id": draft.card_id, "phase": "semantic_start"}, ensure_ascii=False), flush=True)
    semantic_brief = await v9.generate_semantic_brief_with_retry(
        lane=draft.lane,
        card_id=draft.card_id,
        published=baseline,
        baseline=baseline,
        variant_v3=baseline,
        model=semantic_model,
    )
    print(json.dumps({"event": "phase", "card_id": draft.card_id, "phase": "semantic_done"}, ensure_ascii=False), flush=True)
    writer_messages = v9.build_v9_writer_messages(
        v1._messages_for_draft(draft, rules=rules, banned=banned),
        semantic_brief=semantic_brief,
    )
    model, timeout, max_tokens, schema = v1._model_route_for_draft(
        draft,
        rules=rules,
        models=models,
        model_override=writer_model,
    )
    print(json.dumps({"event": "phase", "card_id": draft.card_id, "phase": "writer_start"}, ensure_ascii=False), flush=True)
    v12_generated = await v9.v4._generate_fields_from_messages(
        draft,
        rules=rules,
        messages=writer_messages,
        model=model,
        max_tokens=max_tokens,
        response_schema=schema,
        timeout=timeout,
    )
    print(json.dumps({"event": "phase", "card_id": draft.card_id, "phase": "writer_done"}, ensure_ascii=False), flush=True)
    fluency_issues = v11.find_v11_fluency_issues(v12_generated)
    if fluency_issues:
        v12_generated = await v11.repair_chinese_fluency(
            v12_generated,
            semantic_brief=semantic_brief,
            issues=fluency_issues,
            model=writer_model,
        )
    density_issues = v12.find_v12_density_issues(v12_generated)
    if density_issues:
        v12_generated = await v12.repair_high_density_concise(
            v12_generated,
            semantic_brief=semantic_brief,
            issues=density_issues,
            model=writer_model,
        )
    density_issues = v12.find_v12_density_issues(v12_generated)
    print(json.dumps({"event": "phase", "card_id": draft.card_id, "phase": "title_repair_start"}, ensure_ascii=False), flush=True)
    title_issues_before = v13.find_v13_title_issues(v12_generated)
    v13_generated = await v13.repair_title_independence(
        v12_generated,
        semantic_brief=semantic_brief,
        issues=title_issues_before,
        model=writer_model,
    )
    title_issues_after = v13.find_v13_title_issues(v13_generated)
    if title_issues_after:
        v13_generated = await v13.repair_title_independence(
            v13_generated,
            semantic_brief=semantic_brief,
            issues=title_issues_after,
            model=writer_model,
        )
        title_issues_after = v13.find_v13_title_issues(v13_generated)
    print(json.dumps({"event": "phase", "card_id": draft.card_id, "phase": "title_repair_done"}, ensure_ascii=False), flush=True)
    return baseline, semantic_brief, v12_generated, v13_generated, fluency_issues, density_issues, title_issues_before, title_issues_after


async def run_shadow(*, max_rows: int | None = None) -> list[dict[str, Any]]:
    rules = v1.load_card_content_rules()
    models = v1.load_card_content_models()
    profile = resolve_card_content_llm_profile(models=models, profile_id=V13_PROFILE_ID)
    if profile is None:
        raise ValueError(f"Missing LLM profile: {V13_PROFILE_ID}")
    banned = v1._all_banned_patterns(rules)
    rows: list[dict[str, Any]] = []
    for draft in v12_shadow.load_default_new_samples(max_rows=max_rows):
        row: dict[str, Any] = {
            "context": v12_shadow.sample_context(draft),
            "profile_id": V13_PROFILE_ID,
            "semantic_model": profile["semantic_model"],
            "writer_model": profile["writer_model"],
            "input_baseline": {},
            "semantic_brief": {},
            "v12_shadow": {},
            "v13_shadow": {},
            "fluency_repair_issue_count": 0,
            "remaining_density_issues": [],
            "v13_title_issues_before": [],
            "v13_title_issues_after": [],
            "error": "",
        }
        try:
            baseline, semantic_brief, v12_generated, v13_generated, fluency_issues, density_issues, title_before, title_after = await asyncio.wait_for(
                generate_v13_shadow(
                    draft,
                    rules=rules,
                    models=models,
                    banned=banned,
                    semantic_model=profile["semantic_model"],
                    writer_model=profile["writer_model"],
                ),
                timeout=CARD_TIMEOUT_SECONDS,
            )
            row["input_baseline"] = baseline
            row["semantic_brief"] = semantic_brief
            row["v12_shadow"] = v12_generated
            row["v13_shadow"] = v13_generated
            row["fluency_repair_issue_count"] = len(fluency_issues)
            row["remaining_density_issues"] = density_issues
            row["v13_title_issues_before"] = title_before
            row["v13_title_issues_after"] = title_after
        except asyncio.TimeoutError:
            row["error"] = f"TimeoutError: card generation exceeded {CARD_TIMEOUT_SECONDS:.0f}s"
        except Exception as exc:  # noqa: BLE001 - review packet should keep partial results.
            row["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
        print(json.dumps({"event": "shadow_row", "card_id": draft.card_id, "error": row["error"]}, ensure_ascii=False), flush=True)
    return rows


def _render_field_block(label: str, fields: dict[str, Any]) -> list[str]:
    return v12_shadow._render_field_block(label, fields)


def _render_semantic_brief_block(brief: dict[str, Any]) -> list[str]:
    lines = ["**语义理解 brief**", ""]
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


def render_review_packet(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Hotpost V13 Shadow 新样本人工审核包",
        "",
        "这份报告只读生成，不改 drafts / published / release，也不切默认生产流量。",
        "",
        "审核重点：title 不看 summary_line 是否能懂；正文是否仍保留 V12 的高信息密度、低阅读负担；why_now 是否没有混行动建议；是否还有标题党、报告腔、死物主语或英文缩写挤压。",
        "",
        "## 总览",
        "",
    ]
    for row in rows:
        ctx = row["context"]
        status = "失败" if row["error"] else "成功"
        after_count = len(row.get("v13_title_issues_after") or [])
        lines.append(f"- `{ctx['lane']}` `{ctx['card_id']}`: {status}，title 残留问题 `{after_count}`")
    lines.append("")
    for row in rows:
        ctx = row["context"]
        lines.extend(
            [
                f"## {ctx['lane']} · {ctx['card_id']}",
                "",
                f"- source_scope: `{ctx['source_scope_id']}`",
                f"- topic_pack: `{ctx['topic_pack_id']}`",
                f"- score/comments: `{ctx['score']}` / `{ctx['num_comments']}`",
                f"- source: {ctx['source_link']}",
                f"- model route: `{row['semantic_model']} -> {row['writer_model']}`",
                "",
                "**原始证据**",
                "",
            ]
        )
        for quote in ctx["evidence_quotes"]:
            text = str(quote["text"]).replace("\n", " ")
            if len(text) > 360:
                text = text[:357] + "..."
            lines.append(f"- {quote['community']}: {text}")
        lines.append("")
        if row["error"]:
            lines.extend(["**生成失败**", "", f"- {row['error']}", ""])
            continue
        lines.extend(_render_field_block("当前草稿/候选基线", row["input_baseline"]))
        lines.extend(_render_semantic_brief_block(row.get("semantic_brief") or {}))
        lines.extend(_render_field_block("V12 shadow 输出", row["v12_shadow"]))
        lines.extend(_render_field_block("V13 title-standalone 输出", row["v13_shadow"]))
        lines.extend(
            [
                "**自动检查**",
                "",
                f"- V11 中文顺读 repair 触发问题数：`{row['fluency_repair_issue_count']}`",
                f"- V12 高密度残留问题：`{len(row['remaining_density_issues'])}`",
                f"- V13 title 修前问题：`{len(row['v13_title_issues_before'])}`",
                f"- V13 title 修后问题：`{len(row['v13_title_issues_after'])}`",
            ]
        )
        for issue in row["v13_title_issues_after"][:5]:
            lines.append(f"  - {issue}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    v1.REPORTS_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_MD_PATH.write_text(render_review_packet(rows), encoding="utf-8")
    return REPORT_JSON_PATH, REPORT_MD_PATH


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run Hotpost V13 title-standalone shadow on fresh samples")
    parser.add_argument("--max-rows", type=int, default=None)
    args = parser.parse_args()
    rows = await run_shadow(max_rows=args.max_rows)
    json_path, report_path = write_outputs(rows)
    print(
        json.dumps(
            {"event": "done", "json_path": str(json_path), "report_path": str(report_path), "row_count": len(rows)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
