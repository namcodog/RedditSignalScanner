"""Run Hotpost V12 profile shadow generation on fresh review samples.

This runner is read-only. It does not publish cards, update drafts, or switch
the default production model route.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
load_dotenv(BACKEND_ROOT / ".env")
from app.services.llm.clients import openai_client as openai_client_module  # noqa: E402


openai_client_module.OpenAI = None

from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v1 as v1
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v9 as v9
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v11 as v11
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v12 as v12
from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_card_drafts import ValidationCardDraft, WritingCardDraft
from app.services.hotpost.card_content_llm_router import resolve_card_content_llm_profile
from app.services.hotpost.card_draft_builder import seed_validation_draft
from app.services.hotpost.card_payload_store import load_candidates, load_drafts


REPORT_JSON_PATH = v1.REPORTS_EVALS_DIR / "hotpost_v12_shadow_new_samples_results.json"
REPORT_MD_PATH = v1.REPORTS_EVALS_DIR / "hotpost_v12_shadow_new_samples_review_packet.md"
V12_PROFILE_ID = "hotpost_v12"
OLD_V12_CARD_IDS = {
    "card-cand-ai-automation-1s6pkg3-validate",
    "card-cand-ai-automation-1saabgz-validate",
    "card-cand-ai-automation-1rweoq5-validate",
    "card-cand-ai-automation-1saaqfv-validate",
    "card-group-ai-automation-1de9c05516",
    "card-group-ai-automation-3a7f66c166",
}
DEFAULT_SAMPLE_IDS = {
    "signal": [
        "cand-ai-automation-1sreuhj",
        "cand-business-growth-ops-1stc8hc",
    ],
    "hot": [
        "card-cand-ai-automation-1sd2f37-validate",
        "card-cand-business-growth-ops-1stxbb4-validate",
    ],
    "breakdown": [
        "card-group-ecommerce-sellers-a2cc2d4b93-validate",
        "card-group-ecommerce-sellers-abc138d79b-validate",
    ],
}


def load_default_new_samples(*, max_rows: int | None = None) -> list[ValidationCardDraft | WritingCardDraft]:
    candidates_by_id = {
        item["candidate_id"]: CandidatePack.model_validate(item)
        for item in load_candidates()
        if item.get("candidate_id")
    }
    drafts_by_card_id = {
        item["card_id"]: item
        for item in load_drafts()
        if item.get("card_id") and item.get("card_id") not in OLD_V12_CARD_IDS
    }
    samples: list[ValidationCardDraft | WritingCardDraft] = []
    for candidate_id in DEFAULT_SAMPLE_IDS["signal"]:
        candidate = candidates_by_id[candidate_id]
        samples.append(seed_validation_draft(candidate))
    for lane in ("hot", "breakdown"):
        for card_id in DEFAULT_SAMPLE_IDS[lane]:
            item = drafts_by_card_id[card_id]
            if item["card_type"] == "write":
                samples.append(WritingCardDraft.model_validate(item))
            else:
                samples.append(ValidationCardDraft.model_validate(item))
    return samples[:max_rows] if max_rows is not None else samples


def sample_context(draft: ValidationCardDraft | WritingCardDraft) -> dict[str, Any]:
    return {
        "card_id": draft.card_id,
        "candidate_id": draft.candidate_id,
        "lane": draft.lane,
        "card_type": draft.card_type,
        "source_scope_id": draft.source_scope_id,
        "topic_pack_id": draft.topic_pack_id,
        "title": draft.title,
        "score": draft.score,
        "num_comments": draft.num_comments,
        "time_window": draft.time_window,
        "source_communities": draft.source_communities,
        "source_link": draft.source_link,
        "evidence_quotes": [
            {
                "text": quote.text,
                "community": quote.community,
                "permalink": quote.permalink,
            }
            for quote in draft.evidence_quotes[:3]
        ],
    }


async def generate_v12_shadow(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    rules: dict[str, Any],
    models: dict[str, Any],
    banned: list[str],
    semantic_model: str,
    writer_model: str,
) -> tuple[dict[str, Any], dict[str, Any], list[str], list[str]]:
    input_baseline = v1.extract_fields(draft)
    if not input_baseline.get("title"):
        input_baseline["title"] = draft.title
    print(json.dumps({"event": "phase", "card_id": draft.card_id, "phase": "semantic_start"}, ensure_ascii=False), flush=True)
    semantic_brief = await v9.generate_semantic_brief_with_retry(
        lane=draft.lane,
        card_id=draft.card_id,
        published=input_baseline,
        baseline=input_baseline,
        variant_v3=input_baseline,
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
    generated = await v9.v4._generate_fields_from_messages(
        draft,
        rules=rules,
        messages=writer_messages,
        model=model,
        max_tokens=max_tokens,
        response_schema=schema,
        timeout=timeout,
    )
    print(json.dumps({"event": "phase", "card_id": draft.card_id, "phase": "writer_done"}, ensure_ascii=False), flush=True)
    fluency_issues = v11.find_v11_fluency_issues(generated)
    if fluency_issues:
        generated = await v11.repair_chinese_fluency(
            generated,
            semantic_brief=semantic_brief,
            issues=fluency_issues,
            model=writer_model,
        )
    density_issues = v12.find_v12_density_issues(generated)
    if density_issues:
        generated = await v12.repair_high_density_concise(
            generated,
            semantic_brief=semantic_brief,
            issues=density_issues,
            model=writer_model,
        )
    remaining_density_issues = v12.find_v12_density_issues(generated)
    return input_baseline, generated, fluency_issues, remaining_density_issues


async def run_shadow(*, max_rows: int | None = None) -> list[dict[str, Any]]:
    rules = v1.load_card_content_rules()
    models = v1.load_card_content_models()
    profile = resolve_card_content_llm_profile(models=models, profile_id=V12_PROFILE_ID)
    if profile is None:
        raise ValueError(f"Missing LLM profile: {V12_PROFILE_ID}")
    banned = v1._all_banned_patterns(rules)
    rows: list[dict[str, Any]] = []
    for draft in load_default_new_samples(max_rows=max_rows):
        row: dict[str, Any] = {
            "context": sample_context(draft),
            "profile_id": V12_PROFILE_ID,
            "semantic_model": profile["semantic_model"],
            "writer_model": profile["writer_model"],
            "input_baseline": {},
            "v12_shadow": {},
            "fluency_repair_issue_count": 0,
            "remaining_density_issues": [],
            "error": "",
        }
        try:
            baseline, shadow, fluency_issues, density_issues = await generate_v12_shadow(
                draft,
                rules=rules,
                models=models,
                banned=banned,
                semantic_model=profile["semantic_model"],
                writer_model=profile["writer_model"],
            )
            row["input_baseline"] = baseline
            row["v12_shadow"] = shadow
            row["fluency_repair_issue_count"] = len(fluency_issues)
            row["remaining_density_issues"] = density_issues
        except Exception as exc:  # noqa: BLE001 - review packet should keep partial results.
            row["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
        print(json.dumps({"event": "shadow_row", "card_id": draft.card_id, "error": row["error"]}, ensure_ascii=False), flush=True)
    return rows


def _render_field_block(label: str, fields: dict[str, Any]) -> list[str]:
    lines = [f"**{label}**", ""]
    for field in (
        "title",
        "summary_line",
        "audience",
        "why_now",
        "why_test_now",
        "flashpoint",
        "fight_line",
        "continue_signal",
        "stop_signal",
        "thesis",
        "writing_angle_or_perspective",
        "tension_point_or_why_it_matters",
        "title_hooks",
        "quote_pack",
    ):
        value = fields.get(field)
        if value:
            lines.append(f"- `{field}`: {value}")
    lines.append("")
    return lines


def render_review_packet(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Hotpost V12 Shadow 新样本人工审核包",
        "",
        "这份报告只读生成，不改 drafts / published / release，也不切默认生产流量。",
        "",
        "审核重点：顺读、信息是否被压掉、why_now 是否混行动建议、标题是否标题党、是否有死物主语做人类动作、英文/产品名排版是否可读。",
        "",
        "## 总览",
        "",
    ]
    for row in rows:
        ctx = row["context"]
        status = "失败" if row["error"] else "成功"
        lines.append(f"- `{ctx['lane']}` `{ctx['card_id']}`: {status}")
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
        lines.extend(_render_field_block("V12 profile shadow 输出", row["v12_shadow"]))
        lines.extend(
            [
                "**自动检查**",
                "",
                f"- V11 中文顺读 repair 触发问题数：`{row['fluency_repair_issue_count']}`",
                f"- V12 高密度残留问题：`{len(row['remaining_density_issues'])}`",
            ]
        )
        for issue in row["remaining_density_issues"][:5]:
            lines.append(f"  - {issue}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    v1.REPORTS_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_MD_PATH.write_text(render_review_packet(rows), encoding="utf-8")
    return REPORT_JSON_PATH, REPORT_MD_PATH


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run Hotpost V12 profile shadow on fresh samples")
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
