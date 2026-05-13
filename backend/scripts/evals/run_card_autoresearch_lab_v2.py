from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from typing import Any

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "backend"
EVALS_DIR = ROOT / "reports" / "evals"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _is_placeholder(value: str | None) -> bool:
    normalized = str(value or "").strip().lower()
    return not normalized or normalized.startswith("your_") or "example" in normalized or normalized == "replace_me"


for key, value in dotenv_values(BACKEND_ROOT / ".env").items():
    if value is not None and _is_placeholder(os.getenv(key)):
        os.environ[key] = str(value)

from app.services.hotpost.card_autoresearch_lab import build_keep_discard, run_signal_prompt_lab
from app.services.hotpost.card_content_generator import load_card_content_models, load_card_content_rules
from app.services.hotpost.signal_judge_runner import summarize_predictions
from app.services.hotpost.signal_eval_review_packet_builder import load_jsonl
from app.services.hotpost.signal_polish_experiment import run_signal_polish_variant


DEFAULT_VARIANTS = [
    "baseline_polish_v1",
    "clean_summary_polish_v1",
    "clean_summary_tight_why_now_polish_v1",
]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _chunk_cases(cases: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    if batch_size <= 0 or batch_size >= len(cases):
        return [cases]
    return [cases[index : index + batch_size] for index in range(0, len(cases), batch_size)]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run card autoresearch lab v2 on polish layer")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--variants", nargs="*", default=DEFAULT_VARIANTS)
    args = parser.parse_args()

    cases = load_jsonl(EVALS_DIR / "signal_eval_set_v1.jsonl")
    if args.offset > 0:
        cases = cases[args.offset :]
    if args.limit > 0:
        cases = cases[: args.limit]
    rules = load_card_content_rules()
    model = load_card_content_models()["fast_model"]
    batches = _chunk_cases(cases, args.batch_size)
    aggregate: dict[str, dict[str, Any]] = {
        variant_id: {"variant_id": variant_id, "generated_rows": [], "predictions": []}
        for variant_id in args.variants
    }
    for index, batch_cases in enumerate(batches, start=1):
        print(
            json.dumps(
                {
                    "event": "batch_start",
                    "batch_index": index,
                    "batch_count": len(batches),
                    "case_count": len(batch_cases),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        batch_result = await run_signal_prompt_lab(
            cases=batch_cases,
            variant_ids=list(args.variants),
            judge_prompt_path=EVALS_DIR / "signal_judge_prompt_v1.md",
            model=model,
            timeout=float(rules["timeouts"]["signal_seconds"]),
            rules=rules,
            concurrency=args.concurrency,
            variant_runner=run_signal_polish_variant,
        )
        for item in batch_result["variant_results"]:
            target = aggregate[item["variant_id"]]
            target["generated_rows"].extend(item["generated_rows"])
            target["predictions"].extend(item["predictions"])

    variant_results: list[dict[str, Any]] = []
    for variant_id in args.variants:
        item = aggregate[variant_id]
        item["summary"] = summarize_predictions(item["predictions"], item["generated_rows"])
        variant_results.append(item)

    result = {
        "variant_results": variant_results,
        "keep_discard": build_keep_discard(
            summaries=[item["summary"] for item in variant_results],
            variant_ids=list(args.variants),
        ),
    }

    for item in result["variant_results"]:
        variant_id = item["variant_id"]
        _write_jsonl(EVALS_DIR / f"card_autoresearch_lab_{variant_id}_outputs_v2.jsonl", item["generated_rows"])
        _write_jsonl(EVALS_DIR / f"card_autoresearch_lab_{variant_id}_judge_v2.jsonl", item["predictions"])
        (EVALS_DIR / f"card_autoresearch_lab_{variant_id}_summary_v2.json").write_text(
            json.dumps(item["summary"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    keep_discard_path = EVALS_DIR / "card_autoresearch_lab_keep_discard_v2.json"
    keep_discard_path.write_text(json.dumps(result["keep_discard"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["keep_discard"], ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
