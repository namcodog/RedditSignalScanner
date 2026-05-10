from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _is_placeholder(value: str | None) -> bool:
    normalized = str(value or "").strip().lower()
    return not normalized or normalized.startswith("your_") or "example" in normalized or normalized == "replace_me"


for key, value in dotenv_values(BACKEND_ROOT / ".env").items():
    if value is not None and _is_placeholder(os.getenv(key)):
        os.environ[key] = str(value)

from app.schemas.hotpost_clues import QuotePreview, ValidationDetail
from app.schemas.hotpost_card_drafts import ValidationCardDraft
from app.services.hotpost.card_content_generator import load_card_content_rules
from app.services.hotpost.semantic_readout import finalize_signal_readout
from app.services.hotpost.signal_judge_runner import run_signal_judge, summarize_predictions
from app.services.hotpost.signal_pack_eval_builder import build_signal_pack_eval_cases


EVALS_DIR = ROOT / "reports" / "evals"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _draft_from_case(case: dict) -> ValidationCardDraft:
    bundle = case["input_bundle"]
    output = case["baseline_output"]
    quotes = [QuotePreview.model_validate(item) for item in bundle["evidence_quotes"]]
    source_link = quotes[0].permalink if quotes else ""
    return ValidationCardDraft(
        draft_id=f"{case['eval_case_id']}-organic-canary",
        candidate_id=case["eval_case_id"],
        candidate_ids=[case["eval_case_id"]],
        card_id=f"{case['eval_case_id']}-organic-canary",
        signal_id=f"{case['eval_case_id']}-organic-canary",
        card_type="validate",
        category_id="validate",
        topic_pack_id=bundle.get("topic_pack_id"),
        title=output["title"],
        source_scope_id=bundle["source_scope_id"],
        source_scope_name=bundle["source_scope_name"],
        matched_subreddit=str((bundle.get("source_communities") or ["r/unknown"])[0]).replace("r/", "", 1),
        post_id=case["eval_case_id"],
        source_event_at=None,
        score=0,
        num_comments=0,
        time_window="7d",
        signal_level=bundle["signal_level"],
        why_now_reason=bundle["why_now_reason"],
        thread_count=int(bundle["thread_count"]),
        community_count=int(bundle["community_count"]),
        quote_count=int(bundle["quote_count"]),
        intent_tags=[str(item) for item in bundle.get("intent_tags") or []],
        evidence_quotes=quotes,
        summary_line=output["summary_line"],
        audience=output["audience"],
        why_now=output["why_now"],
        source_link=source_link,
        source_links=[source_link] if source_link else [],
        source_communities=[str(item) for item in bundle.get("source_communities") or []],
        draft_status="draft",
        draft_note="organic canary",
        detail=ValidationDetail.model_validate(output["detail"]),
    )


async def _judge_rows(rows: list[dict]) -> dict:
    predictions = await asyncio.gather(
        *(run_signal_judge(row, prompt_path=EVALS_DIR / "signal_judge_prompt_v1.md") for row in rows)
    )
    return {"predictions": predictions, "summary": summarize_predictions(predictions, rows)}


async def main() -> None:
    cohort = await build_signal_pack_eval_cases(source_scope_id="business-growth-ops", topic_pack_id="organic-discovery")
    cases = cohort["cases"]
    baseline_rows = [
        {
            "eval_case_id": case["eval_case_id"],
            "variant_id": "human_summary_tight_why_now_v1",
            "input_bundle": case["input_bundle"],
            "baseline_output": case["baseline_output"],
        }
        for case in cases
    ]
    variant_rows = []
    rules = load_card_content_rules()
    for case in cases:
        source_draft = _draft_from_case(case)
        draft = finalize_signal_readout(source_draft, source_draft=source_draft, rules=rules)
        variant_rows.append(
            {
                "eval_case_id": case["eval_case_id"],
                "variant_id": "organic_discovery_semantic_readout_v1",
                "input_bundle": case["input_bundle"],
                "baseline_output": {
                    "title": draft.title,
                    "summary_line": draft.summary_line,
                    "audience": draft.audience,
                    "why_now": draft.why_now,
                    "detail": draft.detail.model_dump(mode="json"),
                },
            }
        )
    baseline = await _judge_rows(baseline_rows)
    variant = await _judge_rows(variant_rows)
    _write_jsonl(EVALS_DIR / "organic_discovery_canary_human_summary_tight_why_now_v1_outputs_v1.jsonl", baseline_rows)
    _write_jsonl(EVALS_DIR / "organic_discovery_canary_human_summary_tight_why_now_v1_judge_v1.jsonl", baseline["predictions"])
    _write_jsonl(EVALS_DIR / "organic_discovery_canary_semantic_readout_v1_outputs_v1.jsonl", variant_rows)
    _write_jsonl(EVALS_DIR / "organic_discovery_canary_semantic_readout_v1_judge_v1.jsonl", variant["predictions"])
    (EVALS_DIR / "organic_discovery_canary_human_summary_tight_why_now_v1_summary_v1.json").write_text(json.dumps(baseline["summary"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (EVALS_DIR / "organic_discovery_canary_semantic_readout_v1_summary_v1.json").write_text(json.dumps(variant["summary"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    keep_discard = [
        {
            "variant_id": "human_summary_tight_why_now_v1",
            "pass_rate": float(baseline["summary"]["pass_rate"]),
            "pass_count": baseline["summary"]["pass_count"],
            "fail_count": baseline["summary"]["fail_count"],
            "decision": "baseline",
        },
        {
            "variant_id": "organic_discovery_semantic_readout_v1",
            "pass_rate": float(variant["summary"]["pass_rate"]),
            "pass_count": variant["summary"]["pass_count"],
            "fail_count": variant["summary"]["fail_count"],
            "decision": "production",
        },
    ]
    (EVALS_DIR / "organic_discovery_canary_keep_discard_v1.json").write_text(json.dumps(keep_discard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(keep_discard, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
