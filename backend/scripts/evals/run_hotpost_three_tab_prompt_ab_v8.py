"""Three-tab Hotpost prompt A/B v8 MiMo 2.5 writer comparison.

This read-only runner reuses the v7 two-stage semantic pipeline and copy gate,
but swaps the Chinese writer from Qwen to MiMo v2.5 Pro. Production prompts are
untouched; outputs are written as distinct v8 artifacts.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v7 as v7


REPORTS_EVALS_DIR = v7.REPORTS_EVALS_DIR
SEMANTIC_MODEL = "google/gemini-3-flash-preview"
WRITER_MODEL = "xiaomi/mimo-v2.5-pro"
BASELINE_MODEL = v7.BASELINE_MODEL


def render_v8_markdown_report(rows: list[dict]) -> str:
    report = v7.render_v7_markdown_report(rows)
    return report.replace(
        "# Hotpost 三 Tab Prompt A/B v7 concise-qwen 小样本报告",
        "# Hotpost 三 Tab Prompt A/B v8 flash-mimo25 小样本报告",
        1,
    )


def write_outputs(rows: list[dict]) -> tuple[Path, Path]:
    REPORTS_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v8_flash_mimo25_results.json"
    md_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v8_flash_mimo25_report.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_v8_markdown_report(rows), encoding="utf-8")
    return json_path, md_path


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run three-tab Hotpost prompt A/B v8 flash-mimo25")
    parser.add_argument("--limit-per-lane", type=int, default=2)
    parser.add_argument("--baseline-model", default=BASELINE_MODEL)
    parser.add_argument("--semantic-model", default=SEMANTIC_MODEL)
    parser.add_argument("--writer-model", default=WRITER_MODEL)
    args = parser.parse_args()

    rows = await v7.run_experiment(
        limit_per_lane=args.limit_per_lane,
        baseline_model=args.baseline_model.strip() or BASELINE_MODEL,
        semantic_model=args.semantic_model.strip() or SEMANTIC_MODEL,
        writer_model=args.writer_model.strip() or WRITER_MODEL,
    )
    json_path, md_path = write_outputs(rows)
    print(
        json.dumps(
            {"event": "done", "json_path": str(json_path), "report_path": str(md_path), "row_count": len(rows)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
